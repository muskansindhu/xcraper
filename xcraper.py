import os
import re
import asyncio
from typing import Any, Dict, List, Tuple, Union
from httpx import AsyncClient, Headers
import time
import json
from dotenv import load_dotenv

from utils import find_key, encode_params, find_obj
from constants import GQL_FEATURES
from config import Config
from account import Account
from models import parse_tweets

load_dotenv()

config = Config()

auth_token = os.getenv("AUTH_TOKEN")
proxy = os.getenv("PROXY")

class Xcraper:
    """A class for scraping data using Twitter's GraphQL API."""

    def _get_cursor(self, obj: dict, cursor_type="Bottom") -> str | None:
        if cur := find_obj(obj, lambda x: x.get("cursorType") == cursor_type):
            return cur.get("value")
        return None

    def _get_response_headers(self, headers: Headers) -> Dict[str, str]:
        """Extracts rate limit headers from the response.

        Args:
            headers (Headers): The response headers.

        Returns:
            Dict[str, str]: A dictionary containing rate limit information.
        """
        header_keys = ['x-rate-limit-limit', 'x-rate-limit-remaining', 'x-rate-limit-reset']
        return {key: headers.get(key, '') for key in header_keys}
    
    def _check_rate_limit(self, header_dict: dict) -> bool:
        rate_limit = int(header_dict['x-rate-limit-limit'])
        rem_rate_limit = int(header_dict['x-rate-limit-remaining'])

        if rem_rate_limit < 0.3 * rate_limit:
            return False 
        
        return True

    async def fetch_search_page(
        self,
        client: AsyncClient,
        query: str,
        cursor: str | None,
        features: dict,
        cursor_type: str = "Bottom"
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, Dict[str, str]]:
        """Fetches a single page of search results using Twitter's GraphQL API.

        Args:
            client (AsyncClient): The HTTPX asynchronous client.
            query (str): The search query string.
            cursor (str | None): The cursor for pagination.
            features (dict): GraphQL features.
            cursor_type (str): The type of cursor to use for pagination.

        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]], str, Dict[str, str]]: The response data, entries, next cursor, and response headers.
        """
        # Prepare query variables
        variables = {
            "rawQuery": query,
            "count": 20,
            "product": "Latest",
            "querySource": "typed_query",
        }
        if cursor:
            variables["cursor"] = cursor

        # Construct request parameters
        params = {
            "variables": variables,
            "features": features,
            "fieldToggles": {"withArticleRichContentState": False},
        }

        # Define GraphQL endpoint details
        qid = "nK1dw4oV3k4w5TdtcAdSww"
        name = "SearchTimeline"

        # Send GET request
        response = await client.get(
            f"{Config.GQL_URL}/{qid}/{name}",
            params=encode_params(params)
        )
        if response is None:
            return {}, [], None, {}

        # Parse response
        data = response.json()
        entries = [
            entry for entry_list in find_key(data, "entries")
            for entry in entry_list
            if re.search(r"^(tweet|user)-", entry["entryId"])
        ]

        # Add query to each entry
        for entry in entries:
            entry["query"] = variables["rawQuery"]

        next_cursor = self._get_cursor(data, cursor_type)
        response_headers = self._get_response_headers(response.headers)

        return data, entries, next_cursor, response_headers

    async def search(
        self,
        client: AsyncClient,
        query: str,
        cursor_type: str = "Bottom"
    ):
        """Performs a paginated search query using Twitter's GraphQL API.

        Args:
            client (AsyncClient): The HTTPX asynchronous client.
            query (str): The search query string.
            limit (int): The maximum number of results to fetch (-1 for no limit).
            cursor_type (str): The type of cursor to use for pagination.

        Yields:
            Tuple[Dict[str, Any], List[Dict[str, Any]], str, Dict[str, str]]: The response data, entries, cursor, and response headers.
        """
        features = {**GQL_FEATURES}
        cur, cnt, active = None, 0, True

        while active:
            await asyncio.sleep(3)
            data, entries, next_cursor, response_headers = await self.fetch_search_page(
                client, query, cur, features, cursor_type
            )

            if not entries:
                break

            yield parse_tweets(data), entries, next_cursor, response_headers

            # Update variables for pagination
            cnt += len(entries)
            if not self._check_rate_limit(response_headers):
                active = False
            # elif not next_cursor:
            #     active = False

            cur = next_cursor

async def main():
    xcraper = Xcraper()

    account = Account()
    account.auth_token = auth_token
    client = account.make_client()

    query = "elon musk"

    try:
        tweets = []
        async for data, entries, cursor, response_headers in xcraper.search(client, query):
            print(response_headers)

            if not xcraper._check_rate_limit(response_headers):
                print("Rate limit reached. Exiting loop.")
                break

            
            for tweet in data:
                tweets.append({
                    "id": tweet.id,
                    "url": tweet.url,
                    "text": tweet.rawContent
                })

            print("writing in file")
            with open(f"res.json", "w") as f:
                json.dump(tweets, f, indent=2)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
