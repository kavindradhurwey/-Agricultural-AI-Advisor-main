import os
from groq import Groq
from typing import Dict, List, Any, Optional

class DiseaseAgent:
    """
    Agricultural disease analysis agent using Groq API
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key)
    
    def analyze_disease_symptoms(self, symptoms: str, crop: str = "") -> str:
        """Analyze disease symptoms and provide recommendations"""
        try:
            system_prompt = """You are a plant pathology expert specializing in Indian crop diseases. Provide:
            - Disease identification based on symptoms
            - Treatment recommendations (organic and chemical)
            - Prevention strategies
            - Management practices
            - Cost-effective solutions for small farmers
            
            Focus on common diseases affecting Indian crops."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Crop: {crop}\nSymptoms: {symptoms}\n\nProvide disease analysis and treatment recommendations."}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error analyzing disease symptoms: {str(e)}"
    
    def get_disease_prevention_advice(self, crop: str, season: str = "") -> str:
        """Get disease prevention advice for specific crops"""
        try:
            system_prompt = """You are a crop protection specialist. Provide comprehensive disease prevention strategies including:
            - Preventive measures for common diseases
            - Seasonal disease management
            - Integrated disease management
            - Resistant varieties recommendations
            - Cultural practices for disease prevention
            
            Focus on practical, cost-effective solutions for Indian farmers."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Crop: {crop}\nSeason: {season}\n\nProvide disease prevention recommendations."}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error getting disease prevention advice: {str(e)}"