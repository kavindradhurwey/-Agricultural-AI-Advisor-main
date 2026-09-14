import os
from groq import Groq
from typing import Dict, List, Any, Optional
import yfinance as yf
from datetime import datetime

class FinancialAgent:
    """
    Agricultural financial advisor using Groq API
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key)
    
    def get_commodity_prices(self, commodities: List[str]) -> Dict:
        """Get current commodity prices"""
        try:
            prices = {}
            for commodity in commodities:
                ticker = yf.Ticker(f"{commodity.upper()}=F")
                info = ticker.info
                hist = ticker.history(period="5d")
                
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev = hist['Close'].iloc[0] if len(hist) > 1 else current
                    change = ((current - prev) / prev) * 100
                    
                    prices[commodity] = {
                        "price": round(current, 2),
                        "change": round(change, 2),
                        "currency": "USD"
                    }
            
            return prices
        except Exception as e:
            return {"error": str(e)}
    
    def get_financial_advice(self, query: str, context: str = "") -> str:
        """Get agricultural financial advice"""
        try:
            system_prompt = """You are an agricultural finance expert for Indian farmers. Provide advice on:
            - Agricultural loans (KCC, term loans)
            - Government schemes (PM-KISAN, PMFBY, etc.)
            - Crop insurance and risk management
            - Market strategies and pricing
            - Investment planning
            - Subsidy applications
            
            Give practical, actionable financial guidance."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {context}\n\nQuery: {query}"}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error getting financial advice: {str(e)}"