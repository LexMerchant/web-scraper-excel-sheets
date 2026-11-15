"""Чистые функции разбора HTML: без сети, легко тестировать."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


@dataclass
class Book:
    title: str
    price: float | None
    currency: str
    rating: int | None
    in_stock: bool
    url: str
    image_url: str
    # Поля ниже заполняются только при разборе карточки товара (--details)
    category: str = ""
    upc: str = ""
    stock_count: int | None = None
    reviews: int | None = None
    description: str = ""

    def to_row(self) -> dict:
        return asdict(self)


@dataclass
class ListingPage:
    books: list[Book] = field(default_factory=list)
    next_url: str | None = None


def parse_price(text: str) -> tuple[float | None, str]:
    """Цена из строки: '£51.77' -> (51.77, '£'), '1 299,90 ₽' -> (1299.9, '₽'),
    '$1,299.00' -> (1299.0, '$')."""
    text = (text or "").strip()
    match = re.search(r"\d[\d\s .,]*", text)
    if not match:
        return None, ""
    number = re.sub(r"[\s ]", "", match.group(0)).rstrip(".,")
    # Десятичный разделитель — последний из «.» и «,», если после него 1–2 цифры
    last_sep = max(number.rfind("."), number.rfind(","))
    if last_sep != -1 and 1 <= len(number) - last_sep - 1 <= 2:
        integer, fraction = number[:last_sep], number[last_sep + 1:]
    else:
        integer, fraction = number, ""
    integer = re.sub(r"[.,]", "", integer)
    value = float(f"{integer}.{fraction}" if fraction else integer)
    currency = re.sub(r"[\d\s .,]", "", text)
    return value, currency


def parse_rating(classes: list[str] | None) -> int | None:
    for cls in classes or []:
        if cls in RATING_WORDS:
            return RATING_WORDS[cls]
    return None


def parse_listing(html: str, page_url: str) -> ListingPage:
    soup = BeautifulSoup(html, "lxml")
    result = ListingPage()

    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        if link is None:
            continue
        price, currency = parse_price(_text(card.select_one("p.price_color")))
        availability = _text(card.select_one("p.availability")).lower()
        img = card.select_one("img")
        result.books.append(
            Book(
                title=link.get("title") or link.get_text(strip=True),
                price=price,
                currency=currency,
                rating=parse_rating(_classes(card.select_one("p.star-rating"))),
                in_stock="in stock" in availability,
                url=urljoin(page_url, link.get("href", "")),
                image_url=urljoin(page_url, img.get("src", "")) if img else "",
            )
        )

    next_link = soup.select_one("li.next a")
    if next_link and next_link.get("href"):
        result.next_url = urljoin(page_url, next_link["href"])
    return result


def parse_details(html: str, book: Book) -> Book:
    """Дополняет книгу данными из её карточки."""
    soup = BeautifulSoup(html, "lxml")

    table = {
        _text(row.select_one("th")): _text(row.select_one("td"))
        for row in soup.select("table.table-striped tr")
    }
    book.upc = table.get("UPC", "")
    book.reviews = _to_int(table.get("Number of reviews"))
    stock = re.search(r"\((\d+) available\)", table.get("Availability", ""))
    book.stock_count = int(stock.group(1)) if stock else (0 if not book.in_stock else None)

    crumbs = soup.select("ul.breadcrumb li a")
    # Хлебные крошки: Home > Books > <Категория>
    if len(crumbs) >= 3:
        book.category = crumbs[2].get_text(strip=True)

    desc = soup.select_one("#product_description ~ p")
    book.description = desc.get_text(strip=True) if desc else ""
    return book


def _text(node) -> str:
    return node.get_text(" ", strip=True) if node is not None else ""


def _classes(node) -> list[str]:
    return list(node.get("class", [])) if node is not None else []


def _to_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None
