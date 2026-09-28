import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment


def build_report(raw_xlsx: str, final_xlsx: str):
    df = pd.read_excel(raw_xlsx, sheet_name='Данные')

    agg = defaultdict(lambda: {'qty': 0, 'sum': 0.0})
    for _, r in df.iterrows():
        key = (r['Категория'], r['Товар'])
        agg[key]['qty'] += int(r['Кол-во'])
        agg[key]['sum'] += float(r['Сумма строки'])

    wb = Workbook()
    ws = wb.active
    ws.title = 'Отчёт'

    headers = ['Категория', 'Товар', 'Кол-во, шт.', 'Сумма, руб.']
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal='center')

    total_qty = 0
    total_sum = 0.0
    for (cat, prod), v in sorted(agg.items()):
        ws.append([cat, prod, v['qty'], round(v['sum'], 2)])
        total_qty += v['qty']
        total_sum += v['sum']

    ws.append(['', 'ИТОГО', total_qty, round(total_sum, 2)])
    last = ws.max_row
    for c in ws[last]:
        c.font = Font(bold=True)

    # Автоширина
    for col in 'ABCD':
        ws.column_dimensions[col].width = 20

    wb.save(final_xlsx)
    print(f"     Форматтер: отчёт сохранён в {final_xlsx}")


if __name__ == '__main__':
    raw = sys.argv[1] if len(sys.argv) > 1 else 'report_raw.xlsx'
    final = sys.argv[2] if len(sys.argv) > 2 else 'report.xlsx'
    build_report(raw, final)