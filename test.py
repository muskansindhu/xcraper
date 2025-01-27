import threading
import time
import random
import asyncio  
from queue import Queue
import sqlite3
import json
import logging

from db import AccountDatabaseManager
from xcraper import Xcraper
from account import Account

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
)

db_manager = AccountDatabaseManager()
xcraper = Xcraper()

proxies =[
    "http://sylvan-63kb0:rbJ24YWnCl@185.193.72.215:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@185.199.119.92:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@185.188.77.82:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@185.199.119.70:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.239.114.250:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.249.2.240:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.239.119.182:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.233.49.75:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.249.1.225:3199",
    "http://sylvan-63kb0:rbJ24YWnCl@104.233.51.60:3199",
]

async def scrape_with_account(account, query, tweets, proxy):
    """Handles the scraping process for a single account."""
    username, auth_token, rate_limit_reset_time = account

    if time.time() < rate_limit_reset_time:
        logging.info(f"Account {username} is rate-limited. Waiting.")
        await asyncio.sleep(rate_limit_reset_time - time.time() + 1)

    try:
        account_obj = Account(auth_token)
        client = account_obj.make_client()

        async for data, cursor, response_headers in xcraper.search(client, query):
            if not xcraper._check_rate_limit(response_headers):
                logging.warning("Rate limit reached. Exiting loop.")
                break

            for tweet in data:
                tweets.append({
                    "id": tweet.id,
                    "url": tweet.url,
                    "text": tweet.rawContent,
                })

            print(f"[INFO] Collected {len(tweets)} tweets so far.")

        conn = sqlite3.connect("accounts.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE accounts SET next_reset = ? WHERE username = ?",
            (response_headers.get("x-rate-limit-reset", rate_limit_reset_time), username),
        )
        conn.commit()
        conn.close()

    except Exception as e:
        logging.error(f"Error scraping with account {username}: {e}")


def thread_worker(thread_id, accounts_queue, proxy):
    """Worker function for each thread."""
    tweets = []

    async def process_accounts(accounts):
        query = "elon musk"
        for account in accounts:
            logging.info(f"Thread {thread_id} processing account: {account[0]}")
            await scrape_with_account(account, query, tweets, proxy)

    while True:
        accounts = accounts_queue.get()

        if accounts is None: 
            break
        
        logging.info(f"Thread {thread_id} got {len(accounts)} accounts from queue.")
        asyncio.run(process_accounts(accounts))

        accounts_queue.task_done()

    with open(f"res_thread_{thread_id}.json", "w") as f:
        json.dump(tweets, f, indent=2)
    logging.info(f"Thread {thread_id} finished and saved tweets.")


def main():
    num_threads = 10
    accounts_per_thread = 10
    accounts_queue = Queue()

    logging.info("Fetching accounts and initializing threads.")
    for i in range(num_threads):
        accounts = db_manager.get_accounts(i, accounts_per_thread)
        accounts_queue.put(accounts)

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=thread_worker, args=(i, accounts_queue, proxies[i]))
        t.start()
        threads.append(t)

    accounts_queue.join()

    for _ in range(num_threads):
        accounts_queue.put(None)
    for t in threads:
        t.join()

    logging.info("All threads completed.")


if __name__ == "__main__":
    main()
