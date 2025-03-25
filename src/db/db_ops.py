import datetime
import os
import sqlite3


class DatabaseManager:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'urls.db')
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute('PRAGMA journal_mode=WAL;')
        self.init_db()

    def init_db(self):
        # Initialize the database
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS urls (
                    short_code TEXT PRIMARY KEY,
                    long_url TEXT NOT NULL,
                    expiry TEXT
                )
            ''')

    def insert_url(self, short_code, long_url, expiry):
        # Insert a new URL into the database
        try:
            with self.conn:
                self.conn.execute('INSERT INTO urls (short_code, long_url, expiry) VALUES (?, ?, ?)',
                                  (short_code, long_url, expiry))
        except sqlite3.IntegrityError:
            raise ValueError(f"Short code '{short_code}' already exists")

    def get_url(self, short_code):
        # Retrieve a URL from the database
        cursor = self.conn.cursor()
        cursor.execute('SELECT long_url, expiry FROM urls WHERE short_code = ?', (short_code,))
        result = cursor.fetchone()

        print(f"DEBUG: Checking short code '{short_code}' → Found: {result}")

        if result:
            long_url = result[0]
            expiry = result[1] if result[1] is not None else None
            if expiry and datetime.datetime.fromisoformat(expiry) < datetime.datetime.now():
                return None, expiry
            return long_url, expiry
        return None, None

    def url_exists(self, long_url):
        # Check if a URL already exists in the database
        cursor = self.conn.cursor()
        cursor.execute('SELECT short_code FROM urls WHERE long_url = ?', (long_url,))
        result = cursor.fetchone()
        print(f"DEBUG: Checking if long URL exists '{long_url}' → Found: {result}")  # Debugging line

        return result[0] if result else None

    def close(self):
        """Close the database connection explicitly."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()

