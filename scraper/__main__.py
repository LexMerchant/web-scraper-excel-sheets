"""Запуск: python -m scraper --pages 3 --details --out result/books.xlsx"""

from __future__ import annotations

import argparse
import logging
import sys

from .client import Client
from .exporters import save, to_google_sheet
from .parsing import parse_details, parse_listing

START_URL = "https://books.toscrape.com/catalogue/page-1.html"

log = logging.getLogger("scraper")


def run(args: argparse.Namespace) -> list[dict]:
    client = Client(delay=args.delay)
    books = []
    url, page = args.url, 0

    while url and (args.pages == 0 or page < args.pages):
        page += 1
        log.info("Страница %d: %s", page, url)
        listing = parse_listing(client.get(url), url)
        books.extend(listing.books)
        url = listing.next_url

    if args.min_rating:
        books = [b for b in books if (b.rating or 0) >= args.min_rating]
    if args.max_price is not None:
        books = [b for b in books if b.price is not None and b.price <= args.max_price]

    if args.details:
        for i, book in enumerate(books, start=1):
            log.info("Карточка %d/%d: %s", i, len(books), book.title[:50])
            try:
                parse_details(client.get(book.url), book)
            except RuntimeError as exc:  # одна битая карточка не должна ронять весь сбор
                log.error("%s", exc)

    return [b.to_row() for b in books]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Парсер каталога books.toscrape.com")
    p.add_argument("--url", default=START_URL, help="Стартовая страница каталога")
    p.add_argument("--pages", type=int, default=1, help="Сколько страниц обойти (0 — все)")
    p.add_argument("--details", action="store_true", help="Заходить в карточки за подробностями")
    p.add_argument("--min-rating", type=int, default=0, help="Только книги с рейтингом не ниже N")
    p.add_argument("--max-price", type=float, default=None, help="Только книги не дороже N")
    p.add_argument("--delay", type=float, default=0.5, help="Пауза между запросами, сек")
    p.add_argument("--out", default="result/books.xlsx", help="Файл результата: .xlsx, .csv или .json")
    p.add_argument("--gsheet", help="ID Google Таблицы для выгрузки (необязательно)")
    p.add_argument("--creds", default="service_account.json", help="Ключ сервисного аккаунта Google")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    records = run(args)
    if not records:
        log.warning("Ничего не найдено")
        return 1

    path = save(records, args.out)
    log.info("Сохранено %d записей в %s", len(records), path)

    if args.gsheet:
        url = to_google_sheet(records, args.gsheet, args.creds)
        log.info("Google Таблица обновлена: %s", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
