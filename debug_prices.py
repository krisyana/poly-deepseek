import json
from polymarket import PolymarketClient

def main():
    client = PolymarketClient()
    # Fetch a few events
    events = client.fetch_events(limit=5)
    
    print(f"Fetched {len(events)} events.")
    
    for event in events:
        print(f"\nEvent: {event.get('title')}")
        markets = event.get("markets", [])
        for m in markets:
            print(f"  Market: {m.get('question')}")
            print(f"  Outcomes (Raw): {m.get('outcomes')} (Type: {type(m.get('outcomes'))})")
            print(f"  Prices (Raw): {m.get('outcomePrices')} (Type: {type(m.get('outcomePrices'))})")
            
            # Try parsing
            try:
                outcomes = m.get("outcomes")
                prices = m.get("outcomePrices")
                
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                if isinstance(prices, str):
                    prices = json.loads(prices)
                    
                print(f"  Parsed Outcomes: {outcomes}")
                print(f"  Parsed Prices: {prices}")
                
                if isinstance(outcomes, list) and isinstance(prices, list):
                    for o, p in zip(outcomes, prices):
                        print(f"    - {o}: {p}")
            except Exception as e:
                print(f"  Error parsing: {e}")

if __name__ == "__main__":
    main()
