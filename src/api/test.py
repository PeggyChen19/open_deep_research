import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
email = os.getenv("SUPABASE_EMAIL")
password = os.getenv("SUPABASE_PASSWORD")

# Step 1: Login to Supabase
auth_url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
headers = {
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json"
}
payload = {
    "email": email,
    "password": password
}
res = requests.post(auth_url, headers=headers, json=payload)
data = res.json()

if "access_token" in data:
    token = data["access_token"]
    print("Bearer ", data["access_token"])

else:
    print("❌ Failed to login:", data)
