import datetime

import pytest

from src.core.shortener import Shortener, parse_expiry

URL_TEST_DATA = [
    ("https://example.com", True),
    ("http://google.com/path", True),
    ("", False),
    (None, False),
    ("ftp://invalid.com", False),
    ("not_a_url", False),
]

CUSTOM_CODE_TEST_DATA = [
    ("abc123", True),
    ("XYZ789", True),
    ("ab", False),
    ("a1b2c3d4e5f", False),
    ("abc#def", False),
    ("", False),
    (None, False),
]

SHORTEN_URL_TEST_DATA = [
    ("https://example.com", None, None, "mockedcode", False),
    ("https://example.com", "24h", None, "mockedcode", False),
    ("https://example.com", None, "mycode", "mycode", False),
    ("invalid_url", None, None, None, ValueError),
    ("https://example.com", None, "ab#cd", None, ValueError),
    ("https://example.com", "xyz", None, None, ValueError),
]


@pytest.fixture
def shortener(mocker):
    shortener = Shortener()
    mocker.patch.object(shortener.db, "get_url", return_value=None)
    mocker.patch.object(shortener.db, "url_exists", return_value=None)
    mocker.patch.object(shortener.db, "insert_url", return_value=None)
    return shortener


@pytest.mark.parametrize("url, expected", URL_TEST_DATA)
def test_is_url_valid(shortener, url, expected):
    result = shortener.is_url_valid(url)
    assert result == expected, f"URL '{url}' expected {expected}, got {result}"


@pytest.mark.parametrize("custom_code, expected", CUSTOM_CODE_TEST_DATA)
def test_is_custom_code_valid(shortener, custom_code, expected):
    result = shortener.is_custom_code_valid(custom_code)
    assert result == expected, f"Custom code '{custom_code}' expected {expected}, got {result}"


def test_shorten_url_duplicate(shortener, mocker):
    mocker.patch.object(shortener.db, 'url_exists', return_value="dup_code")
    result = shortener.shorten_url("https://example.com")
    assert result == "dup_code", "Should return existing code for duplicate URL"
    shortener.db.insert_url.assert_not_called()


def test_shorten_url_custom_code_taken(shortener, mocker):
    mocker.patch.object(shortener.db, 'get_url', return_value=("https://other.com", None))
    print(shortener.db.get_url("taken_code"))
    with pytest.raises(ValueError) as exc_info:
        shortener.shorten_url("https://example.com", None, "takencode")
    assert str(exc_info.value) == "Custom code 'takencode' is already in use"


def test_parse_expiry():
    assert parse_expiry(None) is None
    assert parse_expiry("24h").endswith("Z") is False
    assert parse_expiry("2d").endswith("Z") is False
    assert parse_expiry("1w").endswith("Z") is False
    assert parse_expiry("30m").endswith("Z") is False
    with pytest.raises(ValueError):
        parse_expiry("invalid")


@pytest.mark.parametrize("long_url, expiry, custom_code, expected_short_code, raises_exception", SHORTEN_URL_TEST_DATA)
def test_shorten_url(shortener, mocker, long_url, expiry, custom_code, expected_short_code, raises_exception):
    if raises_exception:
        with pytest.raises(raises_exception) as exc_info:
            shortener.shorten_url(long_url, expiry, custom_code)
        assert str(exc_info.value).startswith("Invalid")
    else:
        fixed_time = datetime.datetime(2025, 3, 26, 20, 48, 46, 855330)
        mocker.patch('src.core.shortener.datetime.datetime', autospec=True)
        mocker.patch('src.core.shortener.datetime.datetime.now', return_value=fixed_time)

        if custom_code is None and shortener.db.url_exists(long_url) is None:
            mocker.patch('src.core.shortener.generate_short_code', return_value="mockedcode")
        if custom_code is None and long_url == "https://example.com" and expiry is None:
            mocker.patch.object(shortener.db, 'url_exists', return_value="existing_code")
            expected_short_code = "existing_code"
        result = shortener.shorten_url(long_url, expiry, custom_code)
        assert result == expected_short_code, f"Expected short code '{expected_short_code}', got '{result}'"
        if custom_code or shortener.db.url_exists(long_url) is None:
            expected_expiry = None if expiry is None else (fixed_time + datetime.timedelta(hours=24)).isoformat()
            shortener.db.insert_url.assert_called_once_with(result, long_url, expected_expiry)