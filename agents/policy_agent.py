"""
Policy Agent for Government Schemes
Scrapes and analyzes government schemes from mygov.in based on user profile and queries
Uses trafilatura for web scraping and intelligent filtering with fallback support
"""

import requests
import json
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
import time
import logging
from groq import Groq
import os

# Import storage and scheduling components
try:
    from utils.scheme_storage import SchemeStorageManager
    from utils.scheme_scheduler import SchemeScheduler
    STORAGE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Storage components not available ({e})")
    STORAGE_AVAILABLE = False
    SchemeStorageManager = None
    SchemeScheduler = None

# Import BeautifulSoup for web scraping (trafilatura has dependency issues)
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    print("Warning: BeautifulSoup not available, using mock data only")
    BeautifulSoup = None
    BEAUTIFULSOUP_AVAILABLE = False

# Disable trafilatura for now due to dependency conflicts
TRAFILATURA_AVAILABLE = False

class PolicyAgent:
    """
    Government Policy and Schemes Agent
    Scrapes, analyzes, and recommends government schemes based on user profile
    """
    
    def __init__(self):
        self.base_url = "https://www.mygov.in"
        self.schemes_cache = {}
        self.last_update = None
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Initialize storage and scheduler if available
        if STORAGE_AVAILABLE:
            self.storage_manager = SchemeStorageManager()
            self.scheduler = SchemeScheduler(
                scraping_function=self._scrape_and_return_schemes,
                storage_manager=self.storage_manager,
                schedule_hour=2,  # 2 AM daily
                schedule_minute=0
            )
            # Start the scheduler
            self.scheduler.start_scheduler()
            self.use_persistent_storage = True
        else:
            self.storage_manager = None
            self.scheduler = None
            self.use_persistent_storage = False
        
        # Agricultural scheme keywords for filtering
        self.agricultural_keywords = [
            'farmer', 'agriculture', 'crop', 'irrigation', 'kisan', 'farming',
            'rural', 'livestock', 'dairy', 'fisheries', 'horticulture',
            'organic', 'fertilizer', 'seed', 'loan', 'credit', 'subsidy',
            'pm-kisan', 'kcc', 'soil', 'water', 'harvest', 'storage'
        ]
        
        # Headers for web scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def should_update_cache(self) -> bool:
        """Check if cache needs updating (daily updates)"""
        if not self.last_update:
            return True
        return datetime.now() - self.last_update > timedelta(hours=24)
    
    def scrape_mygov_schemes(self) -> List[Dict[str, Any]]:
        """Scrape government schemes from mygov.in with persistent storage and fallback"""
        schemes = []
        
        try:
            # If using persistent storage, try to get from database first
            if self.use_persistent_storage and self.storage_manager:
                stored_schemes = self.storage_manager.get_all_schemes()
                if stored_schemes:
                    # Convert database format to expected format
                    schemes = self._convert_db_schemes_to_format(stored_schemes)
                    logging.info(f"Retrieved {len(schemes)} schemes from persistent storage")
                    return schemes
            
            # Try web scraping if no stored schemes or storage not available
            if BEAUTIFULSOUP_AVAILABLE:
                schemes = self._scrape_live_schemes()
                
                # Save to persistent storage if available
                if schemes and self.use_persistent_storage and self.storage_manager:
                    stats = self.storage_manager.save_schemes(schemes, scraping_source="api_call")
                    logging.info(f"Saved schemes to storage: {stats}")
            
            # If no schemes found or scraping failed, use mock data
            if not schemes:
                schemes = self._get_mock_schemes()
                
                # Save mock data to storage if persistent storage is available and empty
                if self.use_persistent_storage and self.storage_manager:
                    stored_count = len(self.storage_manager.get_all_schemes())
                    if stored_count == 0:
                        stats = self.storage_manager.save_schemes(schemes, scraping_source="mock_data")
                        logging.info(f"Saved mock schemes to storage: {stats}")
                
        except Exception as e:
            logging.error(f"Error in scheme scraping: {e}")
            # Fallback to mock data
            schemes = self._get_mock_schemes()
        
        return schemes
    
    def _scrape_and_return_schemes(self) -> List[Dict[str, Any]]:
        """Wrapper method for scheduler to call scraping without storage logic"""
        schemes = []
        
        try:
            if BEAUTIFULSOUP_AVAILABLE:
                schemes = self._scrape_live_schemes()
            
            if not schemes:
                schemes = self._get_mock_schemes()
                
        except Exception as e:
            logging.error(f"Error in scheduled scraping: {e}")
            schemes = self._get_mock_schemes()
        
        return schemes
    
    def _convert_db_schemes_to_format(self, db_schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert database scheme format to expected format"""
        converted_schemes = []
        
        for scheme in db_schemes:
            converted_scheme = {
                'title': scheme.get('title', ''),
                'description': scheme.get('description', ''),
                'source_url': scheme.get('source_url', ''),
                'scraped_at': scheme.get('scraped_at', ''),
                'category': scheme.get('category', ''),
                'keywords': scheme.get('keywords', []),
                'relevance_score': scheme.get('relevance_score', 0)
            }
            converted_schemes.append(converted_scheme)
        
        return converted_schemes
    
    def _scrape_live_schemes(self) -> List[Dict[str, Any]]:
        """Attempt to scrape live schemes from mygov.in"""
        schemes = []
        
        # Multiple endpoints to scrape schemes
        scheme_urls = [
            f"{self.base_url}/schemes/",
            f"{self.base_url}/group-issue/agriculture-and-farmers-welfare/",
            f"{self.base_url}/group-issue/rural-development/",
            f"{self.base_url}/schemes-for-farmers/",
        ]
        
        for url in scheme_urls:
            try:
                logging.info(f"Scraping schemes from: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    # Extract content using trafilatura or fallback
                    content = self._extract_content(response.text)
                    
                    if content:
                        # Parse and extract scheme information
                        parsed_schemes = self._parse_scheme_content(content, url)
                        schemes.extend(parsed_schemes)
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logging.warning(f"Error scraping {url}: {e}")
                continue
        
        # Remove duplicates and filter agricultural schemes
        schemes = self._filter_agricultural_schemes(schemes)
        return schemes
    
    def _get_mock_schemes(self) -> List[Dict[str, Any]]:
        """Get mock government schemes for testing and fallback"""
        mock_schemes = [
            {
                'title': 'PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)',
                'description': 'Direct income support of Rs. 6000 per year to small and marginal farmers. The scheme provides financial assistance to farmers in three equal installments of Rs. 2000 each.',
                'source_url': 'https://www.pmkisan.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Direct Benefit Transfer',
                'keywords': ['farmer', 'income', 'support', 'pm-kisan', 'direct', 'benefit', 'small', 'marginal'],
                'relevance_score': 10
            },
            {
                'title': 'Kisan Credit Card (KCC) Scheme',
                'description': 'Provides farmers with timely access to credit for their cultivation and other needs. Offers flexible repayment terms and covers crop loans, post-harvest expenses, and maintenance of farm assets.',
                'source_url': 'https://www.nabard.org/content.aspx?id=570',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Credit Support',
                'keywords': ['credit', 'loan', 'kcc', 'cultivation', 'farming', 'finance', 'crop'],
                'relevance_score': 9
            },
            {
                'title': 'Pradhan Mantri Fasal Bima Yojana (PMFBY)',
                'description': 'Crop insurance scheme providing financial support to farmers in case of crop failure due to natural calamities. Covers all food crops, oilseeds, and annual commercial/horticultural crops.',
                'source_url': 'https://pmfby.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Insurance',
                'keywords': ['insurance', 'crop', 'pmfby', 'natural', 'calamity', 'protection', 'risk'],
                'relevance_score': 8
            },
            {
                'title': 'Soil Health Card Scheme',
                'description': 'Provides soil health cards to farmers with information on nutrient status of their soil along with recommendations on appropriate dosage of nutrients for improving soil health and fertility.',
                'source_url': 'https://soilhealth.dac.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Soil Management',
                'keywords': ['soil', 'health', 'card', 'nutrient', 'fertility', 'testing', 'organic'],
                'relevance_score': 7
            },
            {
                'title': 'Pradhan Mantri Krishi Sinchai Yojana (PMKSY)',
                'description': 'Aims to expand cultivated area under assured irrigation, improve water use efficiency, and introduce sustainable water conservation practices. Focus on micro-irrigation and watershed development.',
                'source_url': 'https://pmksy.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Irrigation',
                'keywords': ['irrigation', 'water', 'conservation', 'micro', 'watershed', 'pmksy', 'efficiency'],
                'relevance_score': 8
            },
            {
                'title': 'National Mission for Sustainable Agriculture (NMSA)',
                'description': 'Promotes sustainable agriculture practices through climate-resilient farming, soil health management, and efficient water use. Includes support for organic farming and integrated pest management.',
                'source_url': 'https://nmsa.dac.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Sustainable Agriculture',
                'keywords': ['sustainable', 'climate', 'organic', 'pest', 'management', 'resilient', 'nmsa'],
                'relevance_score': 7
            },
            {
                'title': 'Sub-Mission on Agricultural Mechanization (SMAM)',
                'description': 'Promotes farm mechanization for increasing efficiency and reducing drudgery. Provides subsidies for purchase of agricultural machinery and equipment.',
                'source_url': 'https://agrimachinery.nic.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Mechanization',
                'keywords': ['mechanization', 'machinery', 'equipment', 'subsidy', 'efficiency', 'technology'],
                'relevance_score': 6
            },
            {
                'title': 'Rashtriya Krishi Vikas Yojana (RKVY)',
                'description': 'State-specific agriculture development program focusing on increasing agricultural productivity and growth. Supports infrastructure development and technology adoption.',
                'source_url': 'https://rkvy.nic.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Development Program',
                'keywords': ['development', 'productivity', 'growth', 'infrastructure', 'technology', 'rkvy'],
                'relevance_score': 6
            },
            {
                'title': 'National Food Security Mission (NFSM)',
                'description': 'Aims to increase production of rice, wheat, pulses, and coarse cereals through area expansion and productivity enhancement. Provides support for quality seeds and technology.',
                'source_url': 'https://nfsm.gov.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Food Security',
                'keywords': ['food', 'security', 'rice', 'wheat', 'pulses', 'cereals', 'seeds', 'nfsm'],
                'relevance_score': 7
            },
            {
                'title': 'Cotton Technology Mission (CTM)',
                'description': 'Specific support for cotton farmers including improved seeds, pest management, and marketing assistance. Focuses on increasing cotton productivity and quality.',
                'source_url': 'https://cotcorp.org.in/',
                'scraped_at': datetime.now().isoformat(),
                'category': 'Crop Specific',
                'keywords': ['cotton', 'technology', 'seeds', 'pest', 'marketing', 'productivity', 'quality'],
                'relevance_score': 9
            }
        ]
        
        return mock_schemes
    
    def _extract_content(self, html_content: str) -> Optional[str]:
        """Extract content using BeautifulSoup or basic text extraction"""
        try:
            if BEAUTIFULSOUP_AVAILABLE and BeautifulSoup:
                # Use BeautifulSoup for content extraction
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                return text
            else:
                # Basic text extraction as fallback
                import re
                # Remove HTML tags
                clean = re.compile('<.*?>')
                text = re.sub(clean, '', html_content)
                return text.strip()
                
        except Exception as e:
            logging.warning(f"Error extracting content: {e}")
            return None
    
    def _parse_scheme_content(self, content: str, source_url: str) -> List[Dict[str, Any]]:
        """Parse extracted content to identify schemes"""
        schemes = []
        
        try:
            # Split content into potential scheme sections
            sections = re.split(r'\n\s*\n', content)
            
            for section in sections:
                if len(section.strip()) < 50:  # Skip very short sections
                    continue
                
                # Look for scheme indicators
                if any(keyword in section.lower() for keyword in ['scheme', 'yojana', 'program', 'initiative']):
                    scheme = self._extract_scheme_details(section, source_url)
                    if scheme:
                        schemes.append(scheme)
        
        except Exception as e:
            logging.warning(f"Error parsing content from {source_url}: {e}")
        
        return schemes
    
    def _extract_scheme_details(self, text: str, source_url: str) -> Optional[Dict[str, Any]]:
        """Extract scheme details from text section"""
        try:
            lines = text.strip().split('\n')
            
            # Try to identify title (usually first line or line with scheme/yojana)
            title = ""
            description = ""
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Potential title indicators
                if any(keyword in line.lower() for keyword in ['scheme', 'yojana', 'program']) and not title:
                    title = line
                elif not title and len(line) < 100 and i < 3:  # First few lines, reasonable length
                    title = line
                elif title and len(line) > 20:  # Description content
                    description += line + " "
            
            if not title:
                title = lines[0].strip() if lines else "Unknown Scheme"
            
            # Clean up description
            description = description.strip()[:500]  # Limit description length
            
            return {
                'title': title,
                'description': description,
                'source_url': source_url,
                'scraped_at': datetime.now().isoformat(),
                'category': 'Government Scheme',
                'keywords': self._extract_keywords(f"{title} {description}")
            }
        
        except Exception as e:
            logging.warning(f"Error extracting scheme details: {e}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from scheme text"""
        keywords = []
        text_lower = text.lower()
        
        # Check for agricultural keywords
        for keyword in self.agricultural_keywords:
            if keyword in text_lower:
                keywords.append(keyword)
        
        # Extract other relevant terms
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
        for word in words[:10]:  # Limit to first 10 words
            if word.lower() not in keywords and len(word) > 3:
                keywords.append(word.lower())
        
        return keywords[:15]  # Limit total keywords
    
    def _filter_agricultural_schemes(self, schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter schemes relevant to agriculture and remove duplicates"""
        filtered_schemes = []
        seen_titles = set()
        
        for scheme in schemes:
            title = scheme.get('title', '').lower()
            
            # Skip duplicates
            if title in seen_titles:
                continue
            
            # Check if scheme is agriculture-related
            text_to_check = f"{scheme.get('title', '')} {scheme.get('description', '')}".lower()
            
            if any(keyword in text_to_check for keyword in self.agricultural_keywords):
                filtered_schemes.append(scheme)
                seen_titles.add(title)
        
        return filtered_schemes
    
    def get_profile_based_schemes(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get schemes based on user profile"""
        if self.should_update_cache():
            self.schemes_cache = self.scrape_mygov_schemes()
            self.last_update = datetime.now()
        
        # Filter schemes based on profile
        relevant_schemes = []
        
        # Extract profile characteristics
        location = user_profile.get('location', '').lower()
        farm_size = user_profile.get('farm_size', 0)
        crops = [crop.lower() for crop in user_profile.get('primary_crops', [])]
        farming_type = user_profile.get('farming_type', '').lower()
        experience = user_profile.get('experience', 0)
        
        for scheme in self.schemes_cache:
            relevance_score = 0
            scheme_text = f"{scheme.get('title', '')} {scheme.get('description', '')}".lower()
            
            # Location-based scoring
            if location and any(loc_word in scheme_text for loc_word in location.split()):
                relevance_score += 2
            
            # Crop-based scoring
            for crop in crops:
                if crop in scheme_text:
                    relevance_score += 3
            
            # Farming type scoring
            if farming_type and farming_type in scheme_text:
                relevance_score += 2
            
            # Farm size considerations
            if farm_size > 0:
                if farm_size <= 2 and any(term in scheme_text for term in ['small', 'marginal', 'micro']):
                    relevance_score += 2
                elif farm_size > 5 and any(term in scheme_text for term in ['large', 'commercial']):
                    relevance_score += 2
            
            # Experience-based scoring
            if experience < 5 and any(term in scheme_text for term in ['new', 'young', 'startup']):
                relevance_score += 1
            
            # General agricultural relevance
            agricultural_matches = sum(1 for keyword in self.agricultural_keywords if keyword in scheme_text)
            relevance_score += min(agricultural_matches, 5)
            
            if relevance_score > 3:  # Minimum relevance threshold
                scheme['relevance_score'] = relevance_score
                relevant_schemes.append(scheme)
        
        # Sort by relevance score
        relevant_schemes.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return relevant_schemes[:10]  # Return top 10 most relevant schemes
    
    def search_schemes_by_query(self, query: str, user_profile: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search schemes based on user query"""
        if self.should_update_cache():
            self.schemes_cache = self.scrape_mygov_schemes()
            self.last_update = datetime.now()
        
        query_lower = query.lower()
        query_words = query_lower.split()
        
        matching_schemes = []
        
        for scheme in self.schemes_cache:
            match_score = 0
            scheme_text = f"{scheme.get('title', '')} {scheme.get('description', '')}".lower()
            
            # Exact phrase matching
            if query_lower in scheme_text:
                match_score += 5
            
            # Individual word matching
            for word in query_words:
                if word in scheme_text:
                    match_score += 1
            
            # Keyword matching
            scheme_keywords = scheme.get('keywords', [])
            for keyword in scheme_keywords:
                if keyword.lower() in query_lower:
                    match_score += 2
            
            if match_score > 0:
                scheme['match_score'] = match_score
                matching_schemes.append(scheme)
        
        # Sort by match score
        matching_schemes.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        return matching_schemes[:8]  # Return top 8 matches
    
    def get_scheme_analysis(self, schemes: List[Dict[str, Any]], user_profile: Dict[str, Any]) -> str:
        """Generate AI analysis of schemes for the user"""
        try:
            # Prepare scheme summaries
            scheme_summaries = []
            for i, scheme in enumerate(schemes[:5], 1):  # Analyze top 5 schemes
                summary = f"{i}. **{scheme.get('title', 'Unknown Scheme')}**\n"
                summary += f"   Description: {scheme.get('description', 'No description available')[:200]}...\n"
                summary += f"   Relevance Score: {scheme.get('relevance_score', scheme.get('match_score', 0))}\n"
                scheme_summaries.append(summary)
            
            # Create analysis prompt
            profile_summary = f"""
            User Profile:
            - Name: {user_profile.get('name', 'Farmer')}
            - Location: {user_profile.get('location', 'Unknown')}
            - Farm Size: {user_profile.get('farm_size', 0)} acres
            - Primary Crops: {', '.join(user_profile.get('primary_crops', []))}
            - Farming Type: {user_profile.get('farming_type', 'Traditional')}
            - Experience: {user_profile.get('experience', 0)} years
            """
            
            schemes_text = "\n".join(scheme_summaries)
            
            system_prompt = """You are an expert agricultural policy advisor specializing in Indian government schemes. 
            Analyze the provided government schemes and create a personalized recommendation report for the farmer.
            
            Focus on:
            1. Which schemes are most suitable for their profile
            2. Eligibility criteria and application process
            3. Benefits and potential impact
            4. Priority order for applications
            5. Any documentation or requirements needed
            
            Provide practical, actionable advice in a clear, farmer-friendly format."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{profile_summary}\n\nRelevant Government Schemes:\n{schemes_text}\n\nPlease provide a detailed analysis and recommendations."}
            ]
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error generating scheme analysis: {e}")
            return "Error generating scheme analysis. Please try again later."
    
    def get_scheme_updates(self) -> Dict[str, Any]:
        """Get information about scheme updates and cache status"""
        return {
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'total_schemes_cached': len(self.schemes_cache),
            'next_update_due': (self.last_update + timedelta(hours=24)).isoformat() if self.last_update else None,
            'cache_valid': not self.should_update_cache()
        }
    
    def force_update_schemes(self) -> bool:
        """Force update of government schemes cache"""
        try:
            if self.use_persistent_storage and self.scheduler:
                # Use scheduler for manual scraping with storage
                result = self.scheduler.run_manual_scraping()
                return result.get("success", False)
            else:
                # Fallback to cache-based update
                self.schemes_cache = self.scrape_mygov_schemes()
                self.last_update = datetime.now()
                return True
        except Exception as e:
            logging.error(f"Error forcing scheme update: {e}")
            return False
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get statistics about persistent storage"""
        if self.use_persistent_storage and self.storage_manager:
            return self.storage_manager.get_storage_stats()
        else:
            return {
                "total_schemes": len(self.schemes_cache),
                "active_schemes": len(self.schemes_cache),
                "last_update": self.last_update.isoformat() if self.last_update else None,
                "storage_type": "memory_cache"
            }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and information"""
        if self.use_persistent_storage and self.scheduler:
            return self.scheduler.get_scheduler_status()
        else:
            return {
                "scheduler_available": False,
                "message": "Persistent storage not available"
            }
    
    def get_scraping_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scraping history"""
        if self.use_persistent_storage and self.storage_manager:
            return self.storage_manager.get_scraping_history(limit)
        else:
            return []
    
    def update_schedule(self, hour: int, minute: int = 0) -> bool:
        """Update the scheduled scraping time"""
        if self.use_persistent_storage and self.scheduler:
            return self.scheduler.update_schedule(hour, minute)
        else:
            return False
    
    def search_stored_schemes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search schemes in persistent storage"""
        if self.use_persistent_storage and self.storage_manager:
            db_schemes = self.storage_manager.search_schemes(query, limit)
            return self._convert_db_schemes_to_format(db_schemes)
        else:
            # Fallback to in-memory search
            return self.search_schemes_by_query(query, {})[:limit]
    
    def cleanup_old_schemes(self, days_old: int = 90) -> int:
        """Clean up old schemes from storage"""
        if self.use_persistent_storage and self.storage_manager:
            return self.storage_manager.clear_old_schemes(days_old)
        else:
            return 0
