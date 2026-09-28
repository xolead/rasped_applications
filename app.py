import csv
import sqlite3
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    create_engine, Column, Integer, String, Numeric, Boolean,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, Session, relationship


# КОНФИГ
CSV_PATH      = 'orders_flat.csv'
FLAT_DB_PATH  = 'flat.db'
NORM_URL      = 'postgresql+psycopg2://postgres:postgres@localhost:5432/shop'

RAW_XLSX      = 'report_raw.xlsx'  
FINAL_XLSX    = 'report.xlsx'      
FORMATTER     = 'formatter.py'      


# МОДЕЛИ
Base = declarative_base()


class Category(Base):
    __tablename__ = 'categories'
    id          = Column(Integer, primary_key=True)
    name        = Column(String(50), nullable=False, unique=True)
    description = Column(String(255))


class Customer(Base):
    __tablename__ = 'customers'
    id               = Column(Integer, primary_key=True)
    name             = Column(String(100), nullable=False)
    phone            = Column(String(20), unique=True, nullable=False)


class Product(Base):
    __tablename__ = 'products'
    id          = Column(Integer, primary_key=True)
    name        = Column(String(150), nullable=False)
    category_id = Column(ForeignKey('categories.id'), nullable=False)
    price       = Column(Numeric(14, 2), nullable=False)
    stock_qty   = Column(Integer, default=0)
    is_active   = Column(Boolean, default=True)
    category    = relationship('Category')


class Order(Base):
    __tablename__ = 'orders'
    id               = Column(Integer, primary_key=True)
    customer_id      = Column(ForeignKey('customers.id'), nullable=False)
    shipping_address = Column(String(255), nullable=False)
    total_amount     = Column(Numeric(16, 2), default=0)
    customer = relationship('Customer')
    items    = relationship('OrderItem', back_populates='order',
                            cascade='all, delete-orphan')


class OrderItem(Base):
    __tablename__ = 'order_items'
    id         = Column(Integer, primary_key=True)
    order_id   = Column(ForeignKey('orders.id'), nullable=False, index=True)
    product_id = Column(ForeignKey('products.id'), nullable=False, index=True)
    unit_price = Column(Numeric(14, 2), nullable=False)
    quantity   = Column(Integer, nullable=False)
    order   = relationship('Order', back_populates='items')
    product = relationship('Product')
    __table_args__ = (
        UniqueConstraint('order_id', 'product_id', name='uq_order_product'),
    )


# ненормализованная БД (SQLite)
def create_flat_db(csv_path=CSV_PATH, db_path=FLAT_DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS flat_orders")
    cur.execute("""
        CREATE TABLE flat_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT, phone TEXT, shipping_address TEXT,
            category TEXT, product_name TEXT,
            unit_price REAL, quantity INTEGER
        )""")
    with open(csv_path, newline='', encoding='utf-8') as f:
        rows = [
            (r['CustomerName'], r['Phone'], r['ShippingAddress'],
             r['Category'], r['ProductName'],
             float(r['UnitPrice']), int(r['Quantity']))
            for r in csv.DictReader(f)
        ]
        cur.executemany("""
            INSERT INTO flat_orders
            (customer_name,phone,shipping_address,category,product_name,unit_price,quantity)
            VALUES (?,?,?,?,?,?,?)""", rows)
    conn.commit(); conn.close()
    print(f"[1/3] Ненормализованная БД создана: {db_path}")


# миграция в нормализованную БД 
def migrate(flat_db_path=FLAT_DB_PATH, norm_url=NORM_URL):
    engine = create_engine(norm_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = Session(bind=engine)

    fc = sqlite3.connect(flat_db_path); fc.row_factory = sqlite3.Row
    rows = fc.execute("SELECT * FROM flat_orders").fetchall()
    fc.close()

    cats, custs, prods, orders = {}, {}, {}, {}

    for row in rows:
        # категория
        if row['category'] not in cats:
            c = Category(name=row['category'], description='')
            session.add(c); session.flush()
            cats[row['category']] = c.id
        cat_id = cats[row['category']]

        # клиент
        if row['phone'] not in custs:
            c = Customer(name=row['customer_name'], phone=row['phone'])
            session.add(c); session.flush()
            custs[row['phone']] = c.id
        cust_id = custs[row['phone']]

        # товар
        pk = (row['product_name'], cat_id)
        if pk not in prods:
            p = Product(name=row['product_name'], category_id=cat_id,
                        price=Decimal(str(row['unit_price'])),
                        stock_qty=0, is_active=True)
            session.add(p); session.flush()
            prods[pk] = p.id
        prod_id = prods[pk]

        # заказ
        ok = (cust_id, row['shipping_address'])
        if ok not in orders:
            o = Order(customer_id=cust_id,
                      shipping_address=row['shipping_address'],
                      total_amount=Decimal('0'))
            session.add(o); session.flush()
            orders[ok] = o
        order = orders[ok]

        # позиция
        up = Decimal(str(row['unit_price']))
        qty = int(row['quantity'])
        ex = session.query(OrderItem).filter_by(
            order_id=order.id, product_id=prod_id).first()
        if ex:
            ex.quantity += qty
        else:
            session.add(OrderItem(order_id=order.id, product_id=prod_id,
                                  unit_price=up, quantity=qty))
        order.total_amount = (order.total_amount or Decimal('0')) + up * qty

    session.commit(); session.close()
    print(f"[2/3] Нормализованная БД заполнена: {norm_url}")


def export_raw_and_call_formatter(norm_url=NORM_URL):
    engine = create_engine(norm_url)
    query = """
        SELECT o.id                        AS "Номер заказа",
               c.name                      AS "Клиент",
               c.phone                     AS "Телефон",
               cat.name                    AS "Категория",
               p.name                      AS "Товар",
               oi.unit_price               AS "Цена ед.",
               oi.quantity                 AS "Кол-во",
               oi.unit_price * oi.quantity AS "Сумма строки",
               o.shipping_address          AS "Адрес доставки"
        FROM orders o
        JOIN customers   c   ON o.customer_id = c.id
        JOIN order_items oi  ON o.id          = oi.order_id
        JOIN products    p   ON oi.product_id = p.id
        JOIN categories  cat ON p.category_id = cat.id
        ORDER BY o.id, p.name;
    """
    df = pd.read_sql_query(query, con=engine)

    with pd.ExcelWriter(RAW_XLSX, engine='openpyxl') as w:
        df.to_excel(w, sheet_name='Данные', index=False)
    print(f"[3/3] Сырые данные выгружены в {RAW_XLSX}")

    print(f"     Вызов внешнего приложения: {FORMATTER}")
    subprocess.run(
        [sys.executable, FORMATTER, RAW_XLSX, FINAL_XLSX],
        check=True
    )


if __name__ == '__main__':
    create_flat_db()
    migrate()
    export_raw_and_call_formatter()
    print("Готово. Итоговый отчёт: report.xlsx")