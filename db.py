import sqlite3
import os
from typing import List, Dict
from utils import format_cookies, generate_ct0

class AccountDatabaseManager:
    def __init__(self, db_name: str = "accounts.db"):
        """
        Initialize the database manager.

        Args:
            db_name (str): Name of the SQLite database file. Defaults to "accounts.db".
        """
        self.db_name = db_name
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Creates the database and accounts table if they don't exist."""
        if os.path.exists(self.db_name):
            print("Database already exists!")
            return

        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                   username TEXT UNIQUE, 
                   password TEXT NOT NULL, 
                   email TEXT NOT NULL, 
                   email_password TEXT NOT NULL, 
                   auth_token TEXT NOT NULL, 
                   cookies TEXT, 
                   stats TEXT, 
                   locks TEXT, 
                   active BOOLEAN, 
                   error TEXT
               )''')

        connection.commit()
        connection.close()

    def parse_account_details(self, filepath: str) -> List[Dict[str, str]]:
        """
        Parses account details from a file into a list of dictionaries.

        Args:
            filepath (str): Path to the file containing account details.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with account details.
        """
        account_details = []

        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                details = line.strip().split(":")
                if len(details) >= 6:
                    account_details.append({
                        "username": details[0],
                        "password": details[1],
                        "email": details[2],
                        "email_password": details[3],
                        "auth_token": details[4],
                        "mfa_code_url": details[5],
                    })

        return account_details

    def insert_account_details(self, filepath: str) -> None:
        """
        Inserts account details into the database.

        Args:
            accounts (List[Dict[str, str]]): A list of dictionaries containing account details.
        """
        accounts = self.parse_account_details(filepath)

        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()

        try:
            for account in accounts:
                cursor.execute(
                    """
                    INSERT INTO accounts (username, password, email, email_password, auth_token, cookies) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        account["username"],
                        account["password"],
                        account["email"],
                        account["email_password"],
                        account["auth_token"],
                        format_cookies(account["auth_token"], generate_ct0())
                    )
                )
            connection.commit()
        except sqlite3.Error as error:
            print(f"Database error: {error}")
        finally:
            connection.close()


if __name__ == "__main__":
    db = AccountDatabaseManager()
    db.insert_account_details("account_creds.txt")

