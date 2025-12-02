import json
import os
from typing import List, Dict, Any
from datetime import datetime

class StorageBackend:
    def load(self) -> Dict[str, Any]:
        raise NotImplementedError
    
    def save(self, data: Dict[str, Any]):
        raise NotImplementedError

class JsonStorage(StorageBackend):
    def __init__(self, filepath: str):
        self.filepath = filepath
        
    def load(self) -> Dict[str, Any]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading JSON: {e}")
        return {"balance": 1000.0, "bets": []}

    def save(self, data: Dict[str, Any]):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving JSON: {e}")

class SupabaseStorage(StorageBackend):
    def __init__(self, url: str, key: str, profile: str):
        from supabase import create_client, Client
        self.supabase: Client = create_client(url, key)
        self.profile = profile
        
    def load(self) -> Dict[str, Any]:
        try:
            response = self.supabase.table("portfolios").select("data").eq("name", self.profile).limit(1).execute()
            if response.data:
                return response.data[0]['data']
        except Exception as e:
            print(f"Error loading from Supabase: {e}")
            
        return {"balance": 1000.0, "bets": []}

    def save(self, data: Dict[str, Any]):
        try:
            # Upsert the portfolio data using profile name as key
            row = {"name": self.profile, "data": data}
            self.supabase.table("portfolios").upsert(row, on_conflict="name").execute()
        except Exception as e:
            print(f"Error saving to Supabase: {e}")

def get_storage(profile: str = "Default") -> StorageBackend:
    # Check for Supabase credentials
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if url and key:
        return SupabaseStorage(url, key, profile)
    
    # Fallback to JSON
    filename = "bets.json" if profile == "Default" else f"bets_{profile}.json"
    return JsonStorage(filename)
