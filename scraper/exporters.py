"""Выгрузка результатов: Excel, CSV, JSON и Google Таблицы."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

# Человеческие названия колонок для отчёта
COLUMNS = {
    "title": "Название",
    "price": "Цена",
    "currency": "Валюта",
    "rating": "Рейтинг",
    "in_stock": "В наличии",
    "stock_count": "Остаток, шт",
    "category": "Категория",
    "upc": "Артикул (UPC)",
    "reviews": "Отзывов",
    "url": "Ссылка",
    "image_url": "Картинка",
    "description": "Описание",
}


def _rows(records: list[dict]) -> tuple[list[str], list[list]]:
    # Пустые колонки (например, детали без --details) в отчёт не выводим
    keys = [k for k in COLUMNS if any(r.get(k) not in (None, "") for r in records)]
    header = [COLUMNS[k] for k in keys]
    body = [[_cell(r.get(k)) for k in keys] for r in records]
    return header, body


def _cell(value):
    if isinstance(value, bool):
        return "да" if value else "нет"
    return "" if value is None else value


def to_excel(records: list[dict], path: Path) -> None:
    header, body = _rows(records)
    wb = Workbook()
    ws = wb.active
    ws.title = "Данные"
    ws.append(header)
    for row in body:
        ws.append(row)

    fill = PatternFill("solid", fgColor="DDEBF7")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for idx, title in enumerate(header, start=1):
        values = [str(title)] + [str(r[idx - 1]) for r in body[:200]]
        width = min(max(len(v) for v in values) + 2, 60)
        ws.column_dimensions[get_column_letter(idx)].width = width
    wb.save(path)


def to_csv(records: list[dict], path: Path) -> None:
    header, body = _rows(records)
    # utf-8-sig — чтобы Excel сразу открыл кириллицу без «кракозябр»
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(header)
        writer.writerows(body)


def to_json(records: list[dict], path: Path) -> None:
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def to_google_sheet(records: list[dict], sheet_id: str, creds_path: str, worksheet: str = "Данные") -> str:
    """Перезаписывает лист Google Таблицы. Нужен сервисный аккаунт Google (см. README)."""
    import gspread  # импорт здесь: библиотека нужна только для этой функции

    gc = gspread.service_account(filename=creds_path)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(worksheet)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet, rows=1, cols=1)
    header, body = _rows(records)
    ws.update([header] + body, value_input_option="USER_ENTERED")
    ws.freeze(rows=1)
    return sh.url


def save(records: list[dict], out: str) -> Path:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        to_excel(records, path)
    elif suffix == ".csv":
        to_csv(records, path)
    elif suffix == ".json":
        to_json(records, path)
    else:
        raise ValueError("Поддерживаются форматы .xlsx, .csv, .json")
    return path
