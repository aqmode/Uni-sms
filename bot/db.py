import sqlite3
import logging

class Database:
    def __init__(self, db_file="uni_sms.db"):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        """Creates the necessary tables if they don't exist."""
        try:
            # Users table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    referred_by INTEGER,
                    balance INTEGER DEFAULT 0, -- Storing balance in cents/kopecks
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Transactions table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'deposit', 'purchase', 'refund'
                    amount INTEGER NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Purchase history
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS purchase_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tzid INTEGER,
                    service TEXT,
                    country TEXT,
                    phone_number TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Rental history
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS rental_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tzid INTEGER,
                    service TEXT,
                    country TEXT,
                    phone_number TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Database setup error: {e}")
            raise

    def add_user(self, telegram_id: int, username: str, first_name: str, referred_by: int = None):
        """Adds a new user to the database."""
        try:
            self.cursor.execute("INSERT OR IGNORE INTO users (telegram_id, username, first_name, referred_by) VALUES (?, ?, ?, ?)",
                                (telegram_id, username, first_name, referred_by))
            self.conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Error adding user: {e}")

    def get_user_id(self, telegram_id: int) -> int:
        """Gets the database ID for a user."""
        self.cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def log_purchase(self, user_telegram_id: int, tzid: int, service: str, country: str, phone_number: str):
        """Logs a new number purchase."""
        user_id = self.get_user_id(user_telegram_id)
        if user_id:
            try:
                self.cursor.execute(
                    "INSERT INTO purchase_history (user_id, tzid, service, country, phone_number, status) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, tzid, service, country, phone_number, 'active')
                )
                self.conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Error logging purchase: {e}")

    def log_rental(self, user_telegram_id: int, tzid: int, service: str, country: str, phone_number: str, expires_at):
        """Logs a new number rental."""
        user_id = self.get_user_id(user_telegram_id)
        if user_id:
            try:
                self.cursor.execute(
                    "INSERT INTO rental_history (user_id, tzid, service, country, phone_number, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, tzid, service, country, phone_number, expires_at)
                )
                self.conn.commit()
            except sqlite3.Error as e:
                logging.error(f"Error logging rental: {e}")

    def get_purchase_history(self, user_telegram_id: int):
        """Retrieves purchase history for a user."""
        user_id = self.get_user_id(user_telegram_id)
        if user_id:
            self.cursor.execute("SELECT service, phone_number, created_at FROM purchase_history WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            return self.cursor.fetchall()
        return []

    def get_rental_history(self, user_telegram_id: int):
        """Retrieves rental history for a user."""
        user_id = self.get_user_id(user_telegram_id)
        if user_id:
            self.cursor.execute("SELECT service, phone_number, expires_at FROM rental_history WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            return self.cursor.fetchall()
        return []

    def get_user_balance(self, user_telegram_id: int) -> int:
        """Retrieves a user's balance in the smallest currency unit."""
        user_id = self.get_user_id(user_telegram_id)
        if user_id:
            self.cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        return 0

    def create_transaction(self, user_telegram_id: int, amount: int, type: str, details: str = None) -> bool:
        """
        Creates a transaction and updates the user's balance.
        Amount should be positive for deposits and negative for withdrawals.
        Returns True on success, False on failure (e.g., insufficient funds).
        """
        user_id = self.get_user_id(user_telegram_id)
        if not user_id:
            return False

        try:
            current_balance = self.get_user_balance(user_telegram_id)

            # For withdrawals, check for sufficient funds
            if amount < 0 and current_balance < abs(amount):
                logging.warning(f"Insufficient funds for user {user_telegram_id} to perform transaction.")
                return False

            # Update balance
            new_balance = current_balance + amount
            self.cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_balance, user_id))

            # Create transaction record
            self.cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, details) VALUES (?, ?, ?, ?)",
                (user_id, type, amount, details)
            )

            self.conn.commit()
            logging.info(f"Transaction successful for user {user_telegram_id}. New balance: {new_balance}")
            return True
        except sqlite3.Error as e:
            logging.error(f"Transaction failed for user {user_telegram_id}: {e}")
            self.conn.rollback()
            return False

    def __del__(self):
        """Closes the database connection on object deletion."""
        if self.conn:
            self.conn.close()
