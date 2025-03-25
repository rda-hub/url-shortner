from datetime import datetime, timedelta
import sqlite3

import pytest
from src.core.shortener import Shortener
from src.db.db_ops import DatabaseManager

URL_TEST_DATA = [
    ("https://example.com", True),
    ("https://google.com/path", True),
    ("http://my-site123.org", True),
    ("not_a_url", False),
    ("", False),
    ("ftp://invalid.com", False),
    (None, False),
    ("https://", False)
]

CUSTOM_CODE_TEST_DATA = [
    ("abc123", True),
    ("XYZ789", True),
    ("code", True),
    ("a1b2c3d4e5", True),
    ("ab", False),
    ("a1b2c3d4e5f", False),
    ("abc#def", False),
    ("", False),
    (None, False),
    ("abc def", False)
]


@pytest.fixture
def real_db():
    db = DatabaseManager()
    db.conn = sqlite3.connect(":memory:")
    db.init_db()
    yield db
    db.close()


@pytest.fixture
def shortener(real_db):
    s = Shortener()
    s.db = real_db
    return s


@pytest.mark.parametrize("url, expected", URL_TEST_DATA)
def test_is_url_valid(shortener, url, expected):
    result = shortener.is_url_valid(url)
    assert result == expected, f"URL '{url}' expected {expected}, got {result}"


@pytest.mark.parametrize("custom_code, expected", CUSTOM_CODE_TEST_DATA)
def test_is_custom_code_valid(shortener, custom_code, expected):
    result = shortener.is_custom_code_valid(custom_code)
    assert result == expected, f"Custom Code '{custom_code}' expected {expected}, got {result}"


def test_shorten_valid_url(real_db, shortener):
    long_url = "https://example.com"
    short_code = shortener.shorten_url(long_url)
    stored_url, expiry = real_db.get_url(short_code)
    assert stored_url == long_url
    assert expiry is None or isinstance(expiry, str)


def test_shorten_invalid_url(shortener):
    invalid_urls = ["not_a_url", "", "ftp://invalid.com", None, "https://"]

    for url in invalid_urls:
        with pytest.raises(ValueError, match=f"Invalid URL '{url}'"):
            shortener.shorten_url(url)


def test_custom_code(real_db, shortener):
    long_url = "https://example.com"
    custom_code = "custom123"
    short_code = shortener.shorten_url(long_url, custom_code=custom_code)
    assert short_code == custom_code
    stored_url, expiry = real_db.get_url(short_code)
    assert stored_url == long_url
    assert expiry is None or isinstance(expiry, str)


def test_shorten_custom_code_conflict(real_db, shortener):
    long_url = "https://example.com"
    custom_code = "custom123"
    real_db.insert_url(custom_code, long_url, None)

    with real_db.conn as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM urls WHERE short_code = ?", (custom_code,))
        count_before = cursor.fetchone()[0]

    with pytest.raises(ValueError, match=f"Custom code '{custom_code}' is already in use"):
        shortener.shorten_url(long_url, custom_code=custom_code)

    with real_db.conn as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM urls WHERE short_code = ?", (custom_code,))
        count_after = cursor.fetchone()[0]
    print(f"DEBUG: Count of '{custom_code}' after calling shorten_url: {count_after}")  # 👀 Debugging statement

    assert count_before == count_after, "Duplicate entry was added to the database!"


def test_shorten_url_with_expiry(real_db, shortener):
    long_url = "https://example.com"
    expiry_time = (datetime.utcnow() + timedelta(days=1)).isoformat()

    short_code = shortener.shorten_url(long_url, expiry=expiry_time)

    stored_url, expiry = real_db.get_url(short_code)

    assert stored_url == long_url, "Stored URL does not match original URL"
    assert expiry is not None, "Expiry should be stored but is None"
    assert expiry == expiry_time, f"Expected expiry {expiry_time}, but got {expiry}"


def test_expired_short_code(real_db, shortener):
    long_url = "https://example.com"
    expired_time = (datetime.utcnow() - timedelta(days=1)).isoformat()  # Expired 1 day ago
    short_code = "expired123"

    real_db.insert_url(short_code, long_url, expired_time)  # Manually inserting expired URL

    result = real_db.get_url(short_code)

    assert result is None or result[1] < datetime.utcnow().isoformat()
    assert result is None or result[0] == None, "Expired URL should not be retrievable"
