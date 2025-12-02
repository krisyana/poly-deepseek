import os
import sys
import argparse
from dotenv import load_dotenv
from client import DeepSeekClient
from analyst import PolymarketAnalyst
from polymarket import PolymarketClient

def main():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        sys.exit(1)

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="DeepSeek Polymarket Predictor")
    parser.add_argument("--category", help="Filter by category (e.g., 'sports', 'politics', 'nba')")
    parser.add_argument("--timeframe", help="Filter by timeframe: '1d', '1w', or 'YYYY-MM-DD'")
    parser.add_argument("--limit", type=int, default=5, help="Max number of events to analyze (default: 5)")
    args = parser.parse_args()

    try:
        client = DeepSeekClient(api_key=api_key)
        analyst = PolymarketAnalyst(client)
        poly_client = PolymarketClient()
    except Exception as e:
        print(f"Error initializing clients: {e}")
        sys.exit(1)

    print("Welcome to the DeepSeek Polymarket Predictor!")
    print("---------------------------------------------")

    market_details_list = []

    if args.category or args.timeframe:
        print(f"Fetching events for category: {args.category or 'Any'}, Timeframe: {args.timeframe or 'Any'}...")
        
        tag_id = None
        if args.category:
            tag_id = poly_client.get_tag_id(args.category)
            if not tag_id:
                print(f"Warning: Could not find tag for category '{args.category}'. Searching without tag.")
        
        # Fetch more events initially to allow for filtering
        events = poly_client.fetch_events(tag_id=tag_id, limit=50)
        
        if args.timeframe:
            events = poly_client.filter_events(events, args.timeframe)
        
        # Limit to requested number
        events = events[:args.limit]
        
        if not events:
            print("No events found matching criteria.")
            sys.exit(0)
            
        print(f"Found {len(events)} events. Analyzing...")
        
        for event in events:
            title = event.get("title", "Unknown Event")
            description = event.get("description", "")
            markets = event.get("markets", [])
            
            market_info = f"Event: {title}\nDescription: {description}\n"
            if markets:
                market_info += "Markets:\n"
                for m in markets:
                    market_info += f"- {m.get('question')} (Odds: {m.get('outcomePrices')})\n"
            
            market_details_list.append(market_info)
            
    else:
        # Interactive mode
        print("Please enter the market details (e.g., match info, odds, context).")
        print("Press Ctrl+D (or Ctrl+Z on Windows) when finished:")

        try:
            # Read multi-line input
            input_text = sys.stdin.read().strip()
            if input_text:
                market_details_list.append(input_text)
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

    if not market_details_list:
        print("No input provided. Exiting.")
        sys.exit(0)

    for i, details in enumerate(market_details_list):
        print(f"\nAnalyzing Event {i+1}/{len(market_details_list)}...")
        print("---------------------------------------------")
        try:
            analysis = analyst.analyze_market(details)
            print("Analysis Result:")
            print("---------------------------------------------")
            print(analysis)
            print("---------------------------------------------")
        except Exception as e:
            print(f"Error during analysis: {e}")

if __name__ == "__main__":
    main()
