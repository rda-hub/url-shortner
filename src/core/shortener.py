import datetime
import re
import uuid
from dateutil.parser import parse as parse_datetime
from src.db.db_ops import DatabaseManager

BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_encode(num):
    if num == 0:
        return BASE62[0]

    encoded = []
    while num:
        num, remainder = divmod(num, 62)
        encoded.append(BASE62[remainder])

    return ''.join(reversed(encoded))


def parse_expiry(expiry):
    if expiry is None:
        return None
    try:
        parse_datetime(expiry)
        return expiry
    except ValueError:
        pass

    if not expiry or not expiry[:-1].isdigit():
        raise ValueError(f"Invalid expiry format '{expiry}'")
    unit = expiry[-1]
    value = int(expiry[:-1])

    if unit == 'h':
        return (datetime.datetime.now() + datetime.timedelta(hours=value)).isoformat()
    elif unit == 'd':
        return (datetime.datetime.now() + datetime.timedelta(days=value)).isoformat()
    elif unit == 'w':
        return (datetime.datetime.now() + datetime.timedelta(weeks=value)).isoformat()
    elif unit == 'm':
        return (datetime.datetime.now() + datetime.timedelta(minutes=value)).isoformat()

    raise ValueError(f"Invalid expiry format '{expiry}'")


def generate_short_code():
    unique_id = uuid.uuid4().int
    short_code = base62_encode(unique_id % (62 ** 6))
    return short_code.zfill(6)


class Shortener:
    def __init__(self):
        self.db = DatabaseManager()

    def is_url_valid(self, long_url):
        # Check if the URL is valid
        if not isinstance(long_url, str) or not long_url.strip():
            return False
        pattern = r'^https?://[a-zA-Z0-9-._~:/?#@!$&\'()*+,;=]+$'
        return bool(re.match(pattern, long_url))

    def is_custom_code_valid(self, custom_code):
        # Check if the custom code is valid
        if not isinstance(custom_code, str) or not custom_code.strip():
            return False
        pattern = r'^[a-zA-Z0-9]{3,10}$'
        return bool(re.match(pattern, custom_code))

    def shorten_url(self, long_url, expiry=None, custom_code=None):
        # Shorten the URL
        if not self.is_url_valid(long_url):
            raise ValueError(f"Invalid URL '{long_url}'")

        with self.db as db:
            if custom_code:
                if not self.is_custom_code_valid(custom_code):
                    raise ValueError(f"Invalid custom code '{custom_code}'")
                if db.get_url(custom_code)[0] is not None:
                    raise ValueError(f"Custom code '{custom_code}' is already in use")
                short_code = custom_code
            else:
                existing_code = db.url_exists(long_url)
                if existing_code:
                    return existing_code
                for _ in range(10):
                    short_code = generate_short_code()
                    if db.get_url(short_code)[0] is None:
                        print("Short code not present in DB. So goint to insert now!!")
                        break
                else:
                    print("WARNING: Switching to UUID-based fallback for unique code generation")
                    short_code = str(uuid.uuid4())[:8]

            parsed_expiry = None
            if expiry:
                try:
                    parsed_expiry = parse_expiry(expiry)
                except ValueError as e:
                    raise ValueError(f"Invalid expiry format '{expiry}': {e}")

            db.insert_url(short_code, long_url, parsed_expiry)
        return short_code
