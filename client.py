import os
import requests
import json
from typing import List, Dict, Any, Optional

class DeepSeekClient:
    """
    A simple wrapper for the DeepSeek API.
    """
    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DeepSeek API key is required. Set DEEPSEEK_API_KEY env var or pass it to the constructor.")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat_completion(self, 
                        messages: List[Dict[str, str]], 
                        model: str = "deepseek-chat", 
                        temperature: float = 1.0,
                        max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Send a chat completion request to DeepSeek API.
        """
        url = f"{self.BASE_URL}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling DeepSeek API: {e}")
            if response is not None:
                print(f"Response body: {response.text}")
            raise e
