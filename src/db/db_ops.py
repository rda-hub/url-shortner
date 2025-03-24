import sqlite3


class DatabaseManager:
    def __init__(self, db_path='data/urls.db'):
        self.conn = sqlite3.connect(db_path)
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
        with self.conn:
            cursor = self.conn.execute('SELECT long_url, expiry FROM urls WHERE short_code = ?',
                                       (short_code,))
            return cursor.fetchone()

    def url_exists(self, long_url):
        # Check if a URL already exists in the database
        with self.conn:
            cursor = self.conn.execute('SELECT short_code FROM urls WHERE long_url = ?',
                                       (long_url,))
            result = cursor.fetchone()
            return result[0] if result else None

    def close(self):
        # Close the database connection
        self.conn.close()
