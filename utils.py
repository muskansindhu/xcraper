import random
import time
import hashlib
import json
from httpx import Headers
from config import Config

def find_key(obj: any, key: str) -> list:
    """
    Find all values of a given key within a nested dict or list of dicts

    Most data of interest is nested, and sometimes defined by different schemas.
    It is not worth our time to enumerate all absolute paths to a given key, then update
    the paths in our parsing functions every time Twitter changes their API.
    Instead, we recursively search for the key here, then run post-processing functions on the results.

    @param obj: dictionary or list of dictionaries
    @param key: key to search for
    @return: list of values
    """

    def helper(obj: any, key: str, L: list) -> list:
        if not obj:
            return L

        if isinstance(obj, list):
            for e in obj:
                L.extend(helper(e, key, []))
            return L

        if isinstance(obj, dict) and obj.get(key):
            L.append(obj[key])

        if isinstance(obj, dict) and obj:
            for k in obj:
                L.extend(helper(obj[k], key, []))
        return L

    return helper(obj, key, [])

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

def encode_params(obj: dict):
    res = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            v = {a: b for a, b in v.items() if b is not None}
            v = json.dumps(v, separators=(",", ":"))

        res[k] = str(v)

    return res

def format_cookies(auth_token, ct0):
    formatted_cookies = "auth_token={}; ct0={}".format(auth_token, ct0)
    return formatted_cookies

def extract_ct0_from_headers(header: Headers) -> dict:
    cookie_str = header.__getitem__('set-cookie')
    cookie_list = cookie_str.split(",")
    for cookie in cookie_list:
        if "ct0=" in cookie:
            cookie = cookie.split(";")
            return cookie[0].strip()

def get_client_headers(auth_token:str) -> dict:
    headers = {}
    ct0 = generate_ct0()

    headers["authorization"] = Config.BEARER_TOKEN
    headers["referer"] = Config.REFERER
    headers["user-agent"] = Config.USER_AGENT

    headers["x-twitter-auth-type"] = ""
    headers["x-twitter-active-user"] = "yes"
    headers["x-twitter-client-language"] = "en"
    headers["x-twitter-auth-type"] = "OAuth2Session"
    headers["content-type"] = "application/json"
    
    headers["x-csrf-token"] = ct0
    headers["cookie"] = "auth_token={}; ct0={}".format(auth_token, ct0)

    return headers