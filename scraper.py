import os
import re
import json
import time
import httpx 
import random
import hashlib
import asyncio
from httpx import Client, AsyncClient

from utils import find_key
from dotenv import load_dotenv
from constants import GQL_FEATURES

load_dotenv()

proxy = os.getenv("PROXY")
auth_token = os.getenv("AUTH_TOKEN")


def generate_ct0() -> str:
    # Seed the random number generator
    random.seed(time.time_ns())
    
    # Generate a random number between 0 and 99,999
    random_num = random.randint(0, 99999)
    
    # Convert the random number to a string
    random_str = str(random_num)
    
    # Create an MD5 hash of the random string
    hash_object = hashlib.md5(random_str.encode())

    hex_hash = hash_object.hexdigest()
    
    return hex_hash


def get_headers(auth_token:str) -> dict:
    headers = {
        "authorization":             "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "referer":                   "https://twitter.com/",
        "user-agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "x-twitter-auth-type":       "",
        "x-twitter-active-user":     "yes",
        "x-twitter-client-language": "en",
    }
    ct0 = generate_ct0()
    headers["x-csrf-token"] = ct0
    headers["cookie"] = "auth_token={}; ct0={}".format(auth_token, ct0)
    headers["x-twitter-auth-type"] = "OAuth2Session"

    return headers


def get_client() -> AsyncClient:
    headers = get_headers(auth_token)
    # client = httpx.AsyncClient(headers=headers, proxy=proxy)
    client = httpx.AsyncClient(headers=headers)
    return client


def get_cursor(data: list | dict) -> str:
    entries = find_key(data, 'entries')
    if entries:
        for entry in entries.pop():
            entry_id = entry.get('entryId', '')
            if ('cursor-bottom' in entry_id) or ('cursor-showmorethreads' in entry_id):
                content = entry['content']
                if itemContent := content.get('itemContent'):
                    return itemContent['value']  # v2 cursor
                return content['value']  # v1 cursor

def encode_params(obj: dict):
    res = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            v = {a: b for a, b in v.items() if b is not None}
            v = json.dumps(v, separators=(",", ":"))

        res[k] = str(v)

    return res

async def get(client: AsyncClient) -> tuple:

    ft = {}

    kv = {
        "rawQuery": "elon musk",
        "count": 20,
        "product": "Latest",
        "querySource": "typed_query",
    }

    params = {"variables": kv, "features": {**GQL_FEATURES, **ft}}
    params["fieldToggles"] = {"withArticleRichContentState": False}

    _, qid, name = {'rawQuery': str, 'product': str}, 'nK1dw4oV3k4w5TdtcAdSww', 'SearchTimeline'

    r = await client.get(f'https://twitter.com/i/api/graphql/{qid}/{name}', params=encode_params(params))
    data = r.json()
    cursor = get_cursor(data)
    entries = [y for x in find_key(data, 'entries') for y in x if re.search(r'^(tweet|user)-', y['entryId'])]

    # headers = r.headers
    # cookies = r.cookies

    for e in entries:
        e['query'] = params['variables']['rawQuery']
    return data, entries, cursor



async def main():
    client = get_client()

    try:
        data, entries, cursor = await get(client)
        print("Data:", data)
        print("Entries:", entries)
        print("Cursor:", cursor)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.aclose()  
asyncio.run(main())