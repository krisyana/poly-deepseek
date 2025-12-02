from typing import Dict, Any
from client import DeepSeekClient

class PolymarketAnalyst:
    """
    Analyst specialized in Polymarket prediction markets.
    """
    
    SYSTEM_PROMPT = """You are a sports betting analyst specializing in Polymarket prediction markets. Your task is to analyze sports matches and return a structured JSON response.

**1. Context Understanding:**
- Market type (Match Winner, Over/Under, Draws, Player Props)
- Current odds and volume
- Time until event settlement

**2. Core Analysis Framework:**
- Team/player recent form
- Head-to-head history
- Home/away performance splits
- Key injuries & suspensions
- Motivational factors

**3. Polymarket-Specific Considerations:**
- Liquidity check
- Time decay
- News sensitivity

**4. Final Output Format (JSON ONLY):**
You must return a valid JSON object with the following structure:
{
    "bets": [
        {
            "market_question": "The exact question of the market you are predicting (copy from input)",
            "prediction": "Yes/No/Team Name",
            "confidence": 0.0 to 1.0,
            "reasoning": "Brief reason",
            "fair_value": 0.0 to 1.0,
            "edge": "X%",
            "recommended_stake": "Low/Medium/High",
            "recommended_amount": 10.0
        }
    ],
    "summary": "Overall analysis summary"
}
"""

    def __init__(self, client: DeepSeekClient):
        self.client = client

    def analyze_market(self, market_details: str, mode: str = "full", model: str = "deepseek-chat", temperature: float = 1.0) -> Dict[str, Any]:
        """
        Analyze a specific market based on the provided details.
        mode: 'full' (detailed) or 'quick' (concise bets only)
        Returns a dictionary with analysis results.
        """
        
        prompt = self.SYSTEM_PROMPT
        if mode == "quick":
            prompt += "\nIMPORTANT: Provide a CONCISE summary and focus primarily on identifying the best bets. Keep reasoning short."
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Analyze this Polymarket event and return JSON:\n\n{market_details}"}
        ]
        
        response = self.client.chat_completion(messages, model=model, temperature=temperature)
        content = response["choices"][0]["message"]["content"]
        
        # Clean content to ensure it's valid JSON (remove markdown code blocks if present)
        content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            import json
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback if JSON fails
            return {
                "prediction": "Error",
                "confidence": 0,
                "reasoning": ["Failed to parse AI response", content[:200]],
                "fair_value": 0,
                "edge": "0%",
                "recommended_stake": "None",
                "recommended_amount": 0
            }
