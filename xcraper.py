import os
import re
import asyncio
from typing import Any, Dict, List, Tuple, Union
from httpx import AsyncClient, Headers

from utils import find_key, encode_params
from dotenv import load_dotenv
from constants import GQL_FEATURES
from config import Config
from account import Account

load_dotenv()

config = Config()

auth_token = os.getenv("AUTH_TOKEN")
proxy = os.getenv("PROXY")

class Xcraper:
    """A class for scraping data using Twitter's GraphQL API."""

    def get_cursor(self, data: Union[List[Any], Dict[str, Any]]) -> str:
        """Extracts the cursor from the provided data.

        Args:
            data (Union[List[Any], Dict[str, Any]]): The response data to search for cursors.

        Returns:
            str: The extracted cursor value, if found.
        """
        entries = find_key(data, 'entries')
        if entries:
            for entry in entries.pop():
                entry_id = entry.get('entryId', '')
                if 'cursor-bottom' in entry_id or 'cursor-showmorethreads' in entry_id:
                    content = entry['content']
                    if item_content := content.get('itemContent'):
                        return item_content['value']  # v2 cursor
                    return content['value']  # v1 cursor
        return ""

    def get_response_headers(self, headers: Headers) -> Dict[str, str]:
        """Extracts rate limit headers from the response.

        Args:
            headers (Headers): The response headers.

        Returns:
            Dict[str, str]: A dictionary containing rate limit information.
        """
        header_keys = ['x-rate-limit-limit', 'x-rate-limit-remaining', 'x-rate-limit-reset']
        return {key: headers.get(key, '') for key in header_keys}

    async def search(self, client: AsyncClient, query: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], str, Dict[str, str]]:
        """Performs a search query using Twitter's GraphQL API.

        Args:
            client (AsyncClient): The HTTPX asynchronous client.
            query (str): The search query string.

        Returns:
            Tuple[Dict[str, Any], List[Dict[str, Any]], str, Dict[str, str]]: The response data, extracted entries, cursor, and response headers.
        """
        # Prepare query variables
        variables = {
            "rawQuery": query,
            "count": 20,
            "product": "Latest",
            "querySource": "typed_query",
        }

        # Construct request parameters
        params = {
            "variables": variables,
            "features": {**GQL_FEATURES},
            "fieldToggles": {"withArticleRichContentState": False},
        }

        # Define GraphQL endpoint details
        qid = 'nK1dw4oV3k4w5TdtcAdSww'
        name = 'SearchTimeline'

        # Send GET request
        response = await client.get(
            f'https://twitter.com/i/api/graphql/{qid}/{name}',
            params=encode_params(params)
        )

        # Parse response
        data = response.json()
        cursor = self.get_cursor(data)
        entries = [
            entry for entry_list in find_key(data, 'entries')
            for entry in entry_list
            if re.search(r'^(tweet|user)-', entry['entryId'])
        ]

        # Extract response headers
        response_headers = self.get_response_headers(response.headers)

        # Add query to each entry
        for entry in entries:
            entry['query'] = variables['rawQuery']

        return data, entries, cursor, response_headers

async def main():
    xcraper = Xcraper()

    account = Account()
    account.auth_token = auth_token
    client = account.make_client()

    query = "elon musk"

    data, entries, cursor, response_headers = await xcraper.search(client, query)

    print(response_headers)


if __name__ == "__main__":
    asyncio.run(main())
    


