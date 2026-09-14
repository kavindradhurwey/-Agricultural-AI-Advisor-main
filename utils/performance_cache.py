"""
Performance optimization utilities with caching
Maintains all functionality while improving speed
"""

import streamlit as st
import hashlib
import pickle
import os
from typing import Any, Optional, Dict
import time
import functools
import logging

logger = logging.getLogger(__name__)

class PerformanceCache:
    """Enhanced caching system for Agricultural AI Advisor"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from function arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cache_result(self, key: str, result: Any, ttl: int = 3600):
        """Cache result with TTL"""
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        cache_data = {
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl
        }
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to cache result: {e}")
    
    def get_cached_result(self, key: str) -> Optional[Any]:
        """Retrieve cached result if valid"""
        cache_file = os.path.join(self.cache_dir, f"{key}.pkl")
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if cache is still valid
            if time.time() - cache_data['timestamp'] < cache_data['ttl']:
                return cache_data['result']
            else:
                # Remove expired cache
                os.remove(cache_file)
                return None
        except Exception as e:
            logger.warning(f"Failed to load cached result: {e}")
            return None

# Global cache instance
performance_cache = PerformanceCache()

def fast_cache(ttl: int = 3600):
    """Decorator for fast caching with TTL"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}_{performance_cache.get_cache_key(*args, **kwargs)}"
            
            # Try to get cached result
            cached_result = performance_cache.get_cached_result(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.info(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            performance_cache.cache_result(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

@st.cache_resource
def load_models_optimized():
    """Optimized model loading with lazy initialization"""
    models = {}
    
    # Load only essential models initially
    logger.info("Loading essential models...")
    
    # Disease detection model (most critical)
    try:
        import tensorflow as tf
        models['disease'] = tf.keras.models.load_model('trained_model.h5')
        logger.info("Disease detection model loaded")
    except Exception as e:
        logger.error(f"Failed to load disease model: {e}")
        models['disease'] = None
    
    return models

@st.cache_data(ttl=1800)  # 30 minutes cache
def cached_weather_data(location: str):
    """Cached weather API calls"""
    from utils.weather_service import WeatherService
    weather_service = WeatherService()
    return weather_service.get_current_weather(location)

@st.cache_data(ttl=3600)  # 1 hour cache
def cached_translation(text: str, target_lang: str = 'en'):
    """Cached translation to avoid repeated API calls"""
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text

@fast_cache(ttl=7200)  # 2 hours cache
def cached_ocr_processing(image_hash: str, image_path: str):
    """Cached OCR processing for identical images"""
    from utils.ocr_processor import OCRProcessor
    ocr_processor = OCRProcessor()
    return ocr_processor.extract_text_from_image(image_path)

def optimize_streamlit_config():
    """Apply Streamlit performance optimizations"""
    st.set_page_config(
        page_title="Agricultural AI Advisor",
        page_icon="🌾",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Performance CSS
    st.markdown("""
    <style>
        /* Reduce animation delays */
        .stApp > div {
            animation-duration: 0.1s !important;
        }
        
        /* Optimize image rendering */
        .stImage > img {
            image-rendering: optimizeSpeed;
        }
        
        /* Reduce sidebar animation */
        .css-1d391kg {
            transition: none !important;
        }
        
        /* Fast scrolling */
        .main .block-container {
            scroll-behavior: auto;
        }
    </style>
    """, unsafe_allow_html=True)

def preload_critical_components():
    """Preload critical components in background"""
    import threading
    
    def background_loader():
        try:
            # Preload OCR engines
            from utils.ocr_processor import OCRProcessor
            ocr = OCRProcessor()
            logger.info("OCR processor preloaded")
            
            # Preload vector database
            from utils.vector_db_handler import VectorDBHandler
            vector_db = VectorDBHandler()
            logger.info("Vector DB handler preloaded")
            
        except Exception as e:
            logger.error(f"Background preloading failed: {e}")
    
    # Start background loading
    thread = threading.Thread(target=background_loader, daemon=True)
    thread.start()

class LazyLoader:
    """Lazy loading for heavy components"""
    
    def __init__(self):
        self._components = {}
    
    def get_component(self, name: str, loader_func):
        """Get component with lazy loading"""
        if name not in self._components:
            logger.info(f"Lazy loading {name}...")
            self._components[name] = loader_func()
        return self._components[name]

# Global lazy loader
lazy_loader = LazyLoader()

def get_disease_detector():
    """Lazy load disease detector"""
    def load_detector():
        from utils.disease_detector import DiseaseDetector
        # Use Docker service URL if available
        DOCKER_SERVICES = {
            'disease_service': 'http://agri-disease-v2:8899'
        }
        return DiseaseDetector(service_url=DOCKER_SERVICES.get('disease_service'))
    
    return lazy_loader.get_component('disease_detector', load_detector)

def get_voice_processor():
    """Lazy load voice processor"""
    def load_voice():
        from utils.voice_processor import VoiceProcessor
        return VoiceProcessor()
    
    return lazy_loader.get_component('voice_processor', load_voice)

def get_agricultural_agents():
    """Lazy load agricultural agents"""
    def load_agents():
        try:
            from agents.agricultural_agents import AgricultureAgentTeam
            return AgricultureAgentTeam()
        except ImportError as e:
            logger.warning(f"Failed to import AgricultureAgentTeam: {e}")
            # Return a mock object with required methods
            class MockAgentTeam:
                def get_government_schemes(self, user_profile, query=""):
                    return "Agricultural schemes information not available"
                def get_market_prices(self, crop_name, location="India"):
                    return "Market price information not available"
                def get_weather_advice(self, location, weather_data):
                    return "Weather advice not available"
            return MockAgentTeam()
    
    return lazy_loader.get_component('agricultural_agents', load_agents)
