import os
from groq import Groq
from typing import Dict, List, Any, Optional
try:
    from ddgs import DDGS  # new package name
except Exception:
    from duckduckgo_search import DDGS  # fallback for older installs

class WebSearchAgent:
    """
    Web search agent for agricultural information
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key)
        self.ddgs = DDGS()
    
    def search_web(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search the web for information"""
        try:
            results = list(self.ddgs.text(f"agriculture {query} India", max_results=max_results))
            return results
        except Exception as e:
            print(f"Web search error: {e}")
            return []
    
    def analyze_search_results(self, query: str, search_results: List[Dict]) -> str:
        """Analyze search results using AI"""
        try:
            context = "\n".join([
                f"Title: {result.get('title', '')}\nContent: {result.get('body', '')}\nSource: {result.get('href', '')}\n"
                for result in search_results[:3]
            ])
            
            system_prompt = """You are an agricultural information analyst. Analyze web search results and provide:
            - Key insights and findings
            - Practical recommendations for farmers
            - Credible source verification
            - Actionable advice based on current information
            
            Focus on Indian agricultural context."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nSearch Results:\n{context}\n\nProvide analysis and recommendations."}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error analyzing search results: {str(e)}"
    
    def search_and_analyze(self, query: str) -> str:
        """Search web and provide AI analysis"""
        search_results = self.search_web(query)
        if search_results:
            return self.analyze_search_results(query, search_results)
        else:
            return "No search results found. Please try a different query."