import os
import json
import sqlite3
from datetime import datetime
from dataclasses import asdict, dataclass, field
from httpx import AsyncClient, AsyncHTTPTransport
from config import Config
from utils import get_client_headers


class Account():
    username: str
    password: str
    email: str
    email_password: str
    active: bool
    auth_token: str
    locks: dict[str, datetime] = field(default_factory=dict)
    stats: dict[str, int] = field(default_factory=dict) 
    headers: dict[str, str] = field(default_factory=dict)
    cookies: str
    mfa_code: str | None = None
    proxy: str | None = None
    error_msg: str | None = None
    last_used: datetime | None = None

    def make_client(self, proxy: str | None = None) -> AsyncClient:
        proxies = [proxy, os.getenv("PROXY"), self.proxy]
        proxies = [x for x in proxies if x is not None]
        proxy = proxies[0] if proxies else None

        transport = AsyncHTTPTransport(retries=2)
        client = AsyncClient(proxy=proxy, follow_redirects=True, transport=transport)

        client.headers = get_client_headers(self.auth_token)

        return client