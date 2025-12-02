import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class BettingSimulator:
    def __init__(self, data_file: str = "bets.json"):
        self.data_file = data_file
        self.balance = 1000.0
        self.bets = []
        self.load_data()

    def load_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.balance = data.get("balance", 1000.0)
                    self.bets = data.get("bets", [])
            except Exception as e:
                print(f"Error loading bets: {e}")
                self.balance = 1000.0
                self.bets = []
        else:
            self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump({
                    "balance": self.balance,
                    "bets": self.bets
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving bets: {e}")

    def place_bet(self, market_question: str, outcome: str, amount: float, price: float, event_title: str, market_id: str = None):
        if amount > self.balance:
            return False, "Insufficient funds"
        
        self.balance -= amount
        bet = {
            "id": len(self.bets) + 1,
            "date": datetime.now().isoformat(),
            "event": event_title,
            "market": market_question,
            "market_id": market_id,
            "outcome": outcome,
            "amount": amount,
            "price": price,
            "current_price": price, # Initialize with entry price
            "potential_payout": amount / price if price > 0 else 0,
            "status": "OPEN", # OPEN, WON, LOST
            "result_checked_at": None
        }
        self.bets.append(bet)
        self.save_data()
        return True, "Bet placed successfully"

    def get_portfolio(self) -> List[Dict]:
        return sorted(self.bets, key=lambda x: x['date'], reverse=True)

    def update_results(self, client):
        """
        Check status of open bets using PolymarketClient.
        Also updates current_price.
        """
        updated_count = 0
        for bet in self.bets:
            if bet["status"] == "OPEN":
                market_id = bet.get("market_id")
                if not market_id:
                    continue
                
                # Fetch market details
                market = client.get_market(market_id)
                if not market:
                    continue
                
                # Update Current Price
                outcome_prices = market.get("outcomePrices")
                outcomes = market.get("outcomes")
                
                # Parse if strings
                if isinstance(outcome_prices, str):
                    import json
                    try: outcome_prices = json.loads(outcome_prices)
                    except: pass
                if isinstance(outcomes, str):
                    import json
                    try: outcomes = json.loads(outcomes)
                    except: pass
                
                # Find price for our outcome
                if isinstance(outcome_prices, list) and isinstance(outcomes, list):
                    try:
                        idx = outcomes.index(bet["outcome"])
                        if idx < len(outcome_prices):
                            new_price = float(outcome_prices[idx])
                            if bet.get("current_price") != new_price:
                                bet["current_price"] = new_price
                                updated_count += 1 # Mark as updated so we save
                    except ValueError:
                        pass # Outcome not found?
                
                # Check if market is closed/resolved
                if market.get("closed") or market.get("resolvedBy"):
                    # Market is resolved
                    # Need to find the winning outcome
                    # Polymarket usually provides 'winner' or we check prices/tokens
                    # For binary markets, it might be in 'outcomePrices' (one is 1, other 0) or 'winner' field?
                    # Let's check 'outcomePrices' first as a heuristic for 100% price
                    
                    # Note: This is a simplification. Real resolution checking might need more complex logic 
                    # depending on market type.
                    
                    outcome_prices = market.get("outcomePrices")
                    if isinstance(outcome_prices, str):
                        import json
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except:
                            pass
                            
                    outcomes = market.get("outcomes")
                    if isinstance(outcomes, str):
                        import json
                        try:
                            outcomes = json.loads(outcomes)
                        except:
                            pass
                    
                    winning_outcome = None
                    if isinstance(outcome_prices, list) and isinstance(outcomes, list):
                        for i, price in enumerate(outcome_prices):
                            if float(price) >= 0.99: # Assuming 1.0 or close to it means winner
                                winning_outcome = outcomes[i]
                                break
                    
                    if winning_outcome:
                        bet["result_checked_at"] = datetime.now().isoformat()
                        if bet["outcome"] == winning_outcome:
                            bet["status"] = "WON"
                            payout = bet["potential_payout"]
                            self.balance += payout
                        else:
                            bet["status"] = "LOST"
                        updated_count += 1
                
        if updated_count > 0:
            self.save_data()
        return updated_count
