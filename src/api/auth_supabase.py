import os
import requests
import time
import threading
from dotenv import load_dotenv

load_dotenv(".env")

_token_lock = threading.Lock()
_token_data = {
    "access_token": None,
    "expires_at": 0  # UNIX timestamp
}

def get_valid_token() -> str:
    with _token_lock:
        now = int(time.time())
        if _token_data["access_token"] and now < _token_data["expires_at"]:
            return _token_data["access_token"]
        print("Token is invalid or expired, fetching a new one...")
        # Invalid or expired token, fetch a new one
        new_token, ttl = fetch_token_from_supabase()
        _token_data["access_token"] = new_token
        _token_data["expires_at"] = now + ttl - 900 # Refresh 15 minutes before expiry
        return new_token

def fetch_token_from_supabase() -> tuple[str, int]:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    EMAIL = os.getenv("SUPABASE_EMAIL")
    PASSWORD = os.getenv("SUPABASE_PASSWORD")

    auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    res = requests.post(auth_url, headers=headers, json=payload)
    if res.status_code != 200:
        raise Exception("Token refresh failed")
    data = res.json()
    if "access_token" in data:
        return data["access_token"], 3600
    else:
        raise Exception("Token refresh failed")