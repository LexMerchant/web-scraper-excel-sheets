from argparse import Namespace
from pathlib import Path

import pytest
from openpyxl import load_workbook

from scraper import __main__ as cli
from scraper.exporters import save
from scraper.parsing import parse_details, parse_listing, parse_price, parse_rating

FIX = Path(__file__).parent / "fixtures"
BASE = "https://books.toscrape.com/catalogue/"


def html(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("£51.77", (51.77, "£")),
        ("1 299,90 ₽", (1299.9, "₽")),
        ("1 500 ₽", (1500.0, "₽")),
        ("$1,299.00", (1299.0, "$")),
        ("12,50 €", (12.5, "€")),
        ("нет цены", (None, "")),
    ],
)
def test_parse_price(text, expected):
    assert parse_price(text) == expected


def test_parse_rating():
    assert parse_rating(["star-rating", "Four"]) == 4
    assert parse_rating(["star-rating"]) is None


def test_parse_listing_cards_and_next():
    page = parse_listing(html("listing_page1.html"), BASE + "page-1.html")
    assert len(page.books) == 2
    first = page.books[0]
    assert first.title == "A Light in the Attic"  # полное название из title, а не обрезанный текст
    assert first.price == 51.77 and first.currency == "£"
    assert first.rating == 3 and first.in_stock is True
    assert first.url == BASE + "a-light-in-the-attic_1000/index.html"
    assert first.image_url.startswith("https://books.toscrape.com/media/")
    assert page.next_url == BASE + "page-2.html"


def test_last_page_has_no_next_and_out_of_stock():
    page = parse_listing(html("listing_page2.html"), BASE + "page-2.html")
    assert page.next_url is None
    assert page.books[0].in_stock is False
    assert page.books[0].price == 12.5


def test_parse_details():
    book = parse_listing(html("listing_page1.html"), BASE + "page-1.html").books[0]
    parse_details(html("detail.html"), book)
    assert book.category == "Poetry"
    assert book.upc == "a897fe39b1053632"
    assert book.stock_count == 22
    assert book.reviews == 0
    assert book.description.startswith("It's hard to imagine")


@pytest.fixture
def fake_site(monkeypatch):
    pages = {
        BASE + "page-1.html": html("listing_page1.html"),
        BASE + "page-2.html": html("listing_page2.html"),
    }
    detail = html("detail.html")
    monkeypatch.setattr(cli.Client, "get", lambda self, url: pages.get(url, detail))


def _args(**kw):
    base = dict(url=BASE + "page-1.html", pages=0, details=False, min_rating=0, max_price=None, delay=0)
    base.update(kw)
    return Namespace(**base)


def test_run_walks_all_pages(fake_site):
    rows = cli.run(_args())
    assert [r["title"] for r in rows] == ["A Light in the Attic", "Tipping the Velvet", "Soumission"]


def test_run_respects_page_limit_and_filters(fake_site):
    assert len(cli.run(_args(pages=1))) == 2
    assert [r["title"] for r in cli.run(_args(min_rating=3))] == ["A Light in the Attic", "Soumission"]
    assert [r["title"] for r in cli.run(_args(max_price=20))] == ["Soumission"]


def test_run_with_details(fake_site):
    rows = cli.run(_args(pages=1, details=True))
    assert all(r["category"] == "Poetry" for r in rows)


@pytest.mark.parametrize("ext", ["xlsx", "csv", "json"])
def test_save_formats(fake_site, tmp_path, ext):
    rows = cli.run(_args())
    path = save(rows, str(tmp_path / f"books.{ext}"))
    assert path.exists() and path.stat().st_size > 0
    if ext == "xlsx":
        ws = load_workbook(path).active
        assert ws["A1"].value == "Название"
        assert ws.max_row == 4
        # колонки деталей без --details пустые и в отчёт не попадают
        assert "Категория" not in [c.value for c in ws[1]]
    if ext == "csv":
        text = path.read_text(encoding="utf-8-sig")
        assert text.splitlines()[0].startswith("Название;Цена")
