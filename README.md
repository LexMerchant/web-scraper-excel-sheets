# Парсер каталога с выгрузкой в Excel, CSV и Google Таблицы

Демо-проект: парсер интернет-каталога на Python. Обходит все страницы каталога, при необходимости заходит в карточку каждого товара и сохраняет результат в удобный отчёт.

В качестве примера используется [books.toscrape.com](https://books.toscrape.com) — учебный сайт, созданный специально для отработки парсинга. Под реальный сайт меняется только модуль `parsing.py`: селекторы и набор полей.

## Что умеет

- обход всех страниц каталога (пагинация) или заданного количества;
- сбор с карточек: название, цена, валюта, рейтинг, наличие, ссылка, картинка;
- режим `--details`: категория, артикул, точный остаток, число отзывов, описание;
- фильтры по рейтингу и цене;
- выгрузка в **Excel** (с шапкой, фильтрами и закреплённой строкой), **CSV** (сразу открывается в Excel с кириллицей), **JSON**;
- выгрузка в **Google Таблицу** через сервисный аккаунт;
- повторы при сетевых ошибках, пауза между запросами, понятные логи;
- если одна карточка не загрузилась, сбор продолжается.

## Установка

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск

```bash
# первые 3 страницы в Excel
python -m scraper --pages 3 --out result/books.xlsx

# весь каталог с подробностями из карточек
python -m scraper --pages 0 --details --out result/books_full.xlsx

# только книги с рейтингом от 4 и дешевле 30 — в CSV
python -m scraper --pages 0 --min-rating 4 --max-price 30 --out result/top.csv

# плюс выгрузка в Google Таблицу
python -m scraper --pages 2 --gsheet <ID_таблицы> --creds service_account.json
```

Все параметры: `python -m scraper --help`.

### Как подключить Google Таблицу

1. В [Google Cloud Console](https://console.cloud.google.com/) создайте проект и включите Google Sheets API.
2. Создайте сервисный аккаунт и скачайте ключ в формате JSON (`service_account.json`).
3. Откройте доступ к таблице на почту сервисного аккаунта (роль «Редактор»).
4. ID таблицы — это часть ссылки между `/d/` и `/edit`.

## Структура

```
scraper/
  parsing.py    — разбор HTML (селекторы, поля)
  client.py     — загрузка страниц: повторы, паузы, кодировка
  exporters.py  — Excel / CSV / JSON / Google Sheets
  __main__.py   — командная строка
tests/          — тесты на сохранённых страницах, без сети
```

## Тесты

```bash
pytest -q
```

Тесты работают на сохранённых HTML-страницах и не ходят в интернет.

## Стек

Python 3.11+, requests, BeautifulSoup4 + lxml, openpyxl, gspread, pytest.
