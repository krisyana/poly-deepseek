import requests
import json

BASE_URL = "https://gamma-api.polymarket.com"

def get_market(market_id):
    try:
        url = f"{BASE_URL}/markets/{market_id}"
        print(f"Fetching {url}...")
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

# Try to fetch a known market ID if we have one, or just list markets to find one
def list_markets():
    try:
        url = f"{BASE_URL}/markets?limit=1"
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error listing: {e}")
        return []

markets = list_markets()
if markets:
    m = markets[0]
    print(f"Found market: {m.get('id')}")
    details = get_market(m.get('id'))
    print(json.dumps(details, indent=2))
else:
    print("No markets found to test.")
