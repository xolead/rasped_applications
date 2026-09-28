import pandas as pd
from sqlalchemy import create_engine, inspect, text

URL = 'postgresql+psycopg2://postgres:postgres@localhost:5432/shop'
engine = create_engine(URL)
insp = inspect(engine)

print("=" * 70)
print("  ТАБЛИЦЫ")
print("=" * 70)
for t in insp.get_table_names():
    print(" -", t)

print("\n" + "=" * 70)
print("  СТРУКТУРА")
print("=" * 70)
for t in insp.get_table_names():
    print(f"\n[{t}]")
    for col in insp.get_columns(t):
        pk = " PK" if col.get('primary_key') else ""
        nn = "" if col['nullable'] else " NOT NULL"
        print(f"   {col['name']:<22} {str(col['type']):<20}{pk}{nn}")
    for fk in insp.get_foreign_keys(t):
        src = ",".join(fk['constrained_columns'])
        dst = f"{fk['referred_table']}.{','.join(fk['referred_columns'])}"
        print(f"   FK: {src} -> {dst}")

print("\n" + "=" * 70)
print("  ДАННЫЕ")
print("=" * 70)
for t in insp.get_table_names():
    df = pd.read_sql(f"SELECT * FROM {t}", engine)
    print(f"\n[{t}] — {len(df)} строк")
    print(df.to_string(index=False) if len(df) else "   (пусто)")