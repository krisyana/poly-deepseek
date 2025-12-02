import requests
from typing import List, Dict, Optional, Union, Any
from datetime import datetime, timedelta
from dateutil import parser

class PolymarketClient:
    """
    Client for interacting with the Polymarket Gamma API.
    """
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        pass

    def get_market(self, market_id: str) -> Optional[Dict]:
        """
        Fetch a single market by ID.
        """
        try:
            response = requests.get(f"{self.BASE_URL}/markets/{market_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching market {market_id}: {e}")
            return None

    def fetch_events(self, tag_id: Union[str, List[str]] = None, limit: int = 20) -> List[Dict]:
        """
        Fetch events from Gamma API.
        If tag_id is provided, filters by that tag.
        If tag_id is a list, fetches from all tags and merges (deduplicating by ID).
        """
        all_events = []
        tag_ids = [tag_id] if isinstance(tag_id, str) else (tag_id or [None])
        
        for tid in tag_ids:
            params = {
                "limit": limit,
                "closed": "false" # Only open events
            }
            if tid:
                params["tag_id"] = tid
                
            try:
                response = requests.get(f"{self.BASE_URL}/events", params=params)
                response.raise_for_status()
                events = response.json()
                all_events.extend(events)
            except Exception as e:
                print(f"Error fetching events for tag {tid}: {e}")
                continue
        
        # Deduplicate by ID
        seen_ids = set()
        unique_events = []
        for e in all_events:
            if e['id'] not in seen_ids:
                unique_events.append(e)
                seen_ids.add(e['id'])
                
        return unique_events

    def filter_events(self, events: List[Dict], timeframe: str) -> List[Dict]:
        """
        Filter events based on timeframe.
        timeframe: '1d', '1w', or specific date 'YYYY-MM-DD'
        """
        filtered_events = []
        now = datetime.now(datetime.now().astimezone().tzinfo)

        target_date = None
        is_specific_date = False

        if timeframe == '1d':
            target_date = now + timedelta(days=1)
        elif timeframe == '1w':
            target_date = now + timedelta(weeks=1)
        else:
            try:
                # Parse specific date (assuming YYYY-MM-DD)
                # We want events ending ON this date (or maybe starting? let's stick to ending/settling for betting relevance)
                # Actually user said "due in 1 day / 1 week or specific date", implying settlement/end date.
                target_date = parser.parse(timeframe).date()
                is_specific_date = True
            except ValueError:
                print(f"Invalid date format: {timeframe}")
                return []

        for event in events:
            # Check markets within the event
            markets = event.get("markets", [])
            if not markets:
                continue
            
            # Strategy: Check multiple date fields to find the most relevant "event date"
            # 1. event.endDate (Settlement)
            # 2. markets[0].endDate (Market Settlement)
            # 3. event.startDate (Event Start - often relevant for "upcoming")
            # 4. event.creationDate (Creation - strictly for "new" events, but user asked for "due in", so settlement is key)
            
            # We prioritize settlement date for "due in" logic
            date_candidates = []
            
            if event.get("endDate"):
                date_candidates.append(event.get("endDate"))
            
            for m in markets:
                if m.get("endDate"):
                    date_candidates.append(m.get("endDate"))
            
            if not date_candidates:
                continue

            # Check if ANY of the dates fall within the range
            # This is permissive: if *any* market in the event settles soon, show it.
            match = False
            for date_str in date_candidates:
                try:
                    # Parse with dateutil (handles ISO 8601 and others)
                    d = parser.parse(date_str)
                    
                    # Ensure timezone awareness for comparison
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=now.tzinfo)
                    
                    if is_specific_date:
                        if d.date() == target_date:
                            match = True
                            break
                    else:
                        # For 1d/1w, we want events ending/settling WITHIN that timeframe from now
                        # We also check if it's in the future (d > now)
                        if now <= d <= target_date:
                            match = True
                            break
                except Exception:
                    continue
            
            if match:
                filtered_events.append(event)

        return filtered_events

    def get_tag_id(self, category: str) -> Optional[str]:
        """
        Helper to map common categories to tag IDs.
        Strategies:
        1. Check hardcoded common aliases.
        2. Search /tags (top 100) for exact or partial match.
        3. Search /sports for matching sport slug, then extract tag ID.
        """
        category = category.lower()
        
        # 1. Hardcoded aliases for known tricky ones or preferences
        aliases = {
            "politics": "375", # Default to US Election (most popular)
            "politic": "375",
            "us election": "375",
            "u.s. election": "375",
            "nba": "745",      # Force NBA ID to avoid WNBA partial match
            "nfl": "450",
            "football": "450", # Default to NFL
            "soccer": ["100350", "306", "1234"], # Soccer (General), EPL (306), UCL (1234)
            "epl": "306",
            "ucl": "1234",
            "champions league": "1234",
            "crypto": "163",    # Default to Bitcoin (Tag ID 163) as "Crypto" isn't a direct tag
            "bitcoin": "163",
        }
        search_term = aliases.get(category, category)
        
        # If it's a list (already resolved alias), return it
        if isinstance(search_term, list):
            return search_term

        # If it's a numeric ID, return it
        if search_term.isdigit():
            return search_term

        # 2. Search /tags (Top 100)
        try:
            url = f"{self.BASE_URL}/tags"
            response = requests.get(url)
            response.raise_for_status()
            tags = response.json()
            
            # Exact match first
            for tag in tags:
                label = (tag.get("label") or "").lower()
                slug = (tag.get("slug") or "").lower()
                if label == search_term or slug == search_term:
                    return tag.get("id")
            
            # Partial match (if exact fails)
            for tag in tags:
                label = (tag.get("label") or "").lower()
                slug = (tag.get("slug") or "").lower()
                if search_term in label or search_term in slug:
                    return tag.get("id")
                    
        except Exception as e:
            print(f"Warning: Error fetching tags: {e}")

        # 3. Search /sports
        try:
            url = f"{self.BASE_URL}/sports"
            response = requests.get(url)
            response.raise_for_status()
            sports = response.json()
            
            # Exact match first
            for sport in sports:
                sport_slug = (sport.get("sport") or "").lower()
                if sport_slug == search_term:
                    tags_str = sport.get("tags")
                    if tags_str:
                        tag_ids = tags_str.split(",")
                        for tid in tag_ids:
                            if tid != "1":
                                return tid

            # Partial match
            for sport in sports:
                sport_slug = (sport.get("sport") or "").lower()
                if search_term in sport_slug:
                    tags_str = sport.get("tags")
                    if tags_str:
                        tag_ids = tags_str.split(",")
                        for tid in tag_ids:
                            if tid != "1":
                                return tid
                                
        except Exception as e:
            print(f"Warning: Error fetching sports: {e}")

        # 4. Fallback: If the category was in our aliases (explicitly supported), return the search_term
        # This allows "crypto" to be returned even if not found in top 100 tags
        if category in aliases:
            return aliases[category]

        return None
