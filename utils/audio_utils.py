import os
import tempfile
import logging
from typing import Optional
import streamlit as st
from gtts import gTTS
import io
import base64

class AudioUtils:
    """
    Utility functions for audio processing in the agricultural AI advisor
    """
    
    def __init__(self):
        self.supported_languages = {
            "English": "en",
            "हिन्दी (Hindi)": "hi", 
            "Hindi": "hi",
            "தமிழ் (Tamil)": "ta",
            "Tamil": "ta",
            "తెలుగు (Telugu)": "te", 
            "Telugu": "te",
            "বাংলা (Bengali)": "bn",
            "Bengali": "bn"
        }
    
    def text_to_speech(self, text: str, language: str = "English") -> Optional[str]:
        """Convert text to speech using gTTS and return base64 encoded audio"""
        try:
            # Get language code
            lang_code = self.supported_languages.get(language, "en")
            
            # Create gTTS object
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Save to bytes
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            
            # Encode to base64 for embedding in HTML
            audio_base64 = base64.b64encode(mp3_fp.read()).decode()
            
            return audio_base64
            
        except Exception as e:
            logging.error(f"Error converting text to speech: {str(e)}")
            return None
    
    def create_audio_player(self, audio_base64: str, text: str = "Play Audio") -> str:
        """Create HTML audio player from base64 encoded audio"""
        try:
            audio_html = f"""
            <div style="margin: 10px 0;">
                <audio controls style="width: 100%;">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    Your browser does not support the audio element.
                </audio>
                <p style="font-size: 12px; color: #666; margin-top: 5px;">🔊 {text}</p>
            </div>
            """
            return audio_html
        except Exception as e:
            logging.error(f"Error creating audio player: {str(e)}")
            return f"<p>Audio playback unavailable: {str(e)}</p>"
    
    def save_audio_file(self, text: str, language: str = "English", filename: str = None) -> Optional[str]:
        """Save TTS audio to a temporary file and return the path"""
        try:
            lang_code = self.supported_languages.get(language, "en")
            
            # Create TTS object
            tts = gTTS(text=text, lang=lang_code, slow=False)
            
            # Generate filename if not provided
            if not filename:
                filename = f"tts_audio_{hash(text) % 1000000}.mp3"
            
            # Create temporary file
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, filename)
            
            # Save audio file
            tts.save(audio_path)
            
            return audio_path
            
        except Exception as e:
            logging.error(f"Error saving audio file: {str(e)}")
            return None
    
    def display_audio_response(self, text: str, language: str = "English"):
        """Display text with audio playback option"""
        try:
            # Display the text
            st.write(text)
            
            # Generate audio
            audio_base64 = self.text_to_speech(text, language)
            
            if audio_base64:
                # Create audio player
                audio_html = self.create_audio_player(audio_base64, "Listen to response")
                
                # Display audio player
                st.markdown(audio_html, unsafe_allow_html=True)
            else:
                st.info("🔊 Audio generation not available for this response")
                
        except Exception as e:
            logging.error(f"Error displaying audio response: {str(e)}")
            st.error(f"Audio display error: {str(e)}")
    
    def process_audio_input(self, audio_bytes) -> Optional[str]:
        """Process audio input and return transcribed text"""
        try:
            # This is a placeholder for audio processing
            # In a real implementation, you would use speech recognition here
            
            if audio_bytes is None:
                return None
            
            # For now, return a message indicating audio was received
            return "Audio input received - transcription feature requires additional setup"
            
        except Exception as e:
            logging.error(f"Error processing audio input: {str(e)}")
            return None
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages for TTS"""
        return list(self.supported_languages.keys())
    
    def validate_language(self, language: str) -> str:
        """Validate and return proper language code"""
        if language in self.supported_languages:
            return self.supported_languages[language]
        else:
            logging.warning(f"Unsupported language: {language}, defaulting to English")
            return "en"
    
    def create_voice_input_interface(self):
        """Create voice input interface using Streamlit audio_input"""
        try:
            st.markdown("### 🎤 Voice Input")
            st.write("Click the record button below and speak your question:")
            
            # Audio input widget
            audio_bytes = st.audio_input("Record your question")
            
            if audio_bytes:
                st.success("✅ Audio recorded successfully!")
                st.write("🔄 Processing audio... (This feature requires additional setup)")
                
                # Play back the recorded audio
                st.audio(audio_bytes, format='audio/wav')
                
                # Return placeholder text for now
                return "Voice input received - please use text input for now"
            
            return None
            
        except Exception as e:
            logging.error(f"Error creating voice input interface: {str(e)}")
            st.error(f"Voice input error: {str(e)}")
            return None
    
    def create_multilingual_audio(self, text: str, languages: list = None) -> dict:
        """Create audio in multiple languages"""
        try:
            if not languages:
                languages = ["English", "Hindi"]
            
            audio_files = {}
            
            for lang in languages:
                if lang in self.supported_languages:
                    audio_base64 = self.text_to_speech(text, lang)
                    if audio_base64:
                        audio_files[lang] = audio_base64
            
            return audio_files
            
        except Exception as e:
            logging.error(f"Error creating multilingual audio: {str(e)}")
            return {}
    
    def display_multilingual_audio(self, text: str, languages: list = None):
        """Display audio players for multiple languages"""
        try:
            if not languages:
                languages = ["English", "Hindi"]
            
            st.markdown("### 🌍 Listen in Different Languages")
            
            # Create tabs for different languages
            tabs = st.tabs(languages)
            
            for i, lang in enumerate(languages):
                with tabs[i]:
                    audio_base64 = self.text_to_speech(text, lang)
                    if audio_base64:
                        audio_html = self.create_audio_player(audio_base64, f"Listen in {lang}")
                        st.markdown(audio_html, unsafe_allow_html=True)
                    else:
                        st.info(f"Audio not available in {lang}")
            
        except Exception as e:
            logging.error(f"Error displaying multilingual audio: {str(e)}")
            st.error(f"Multilingual audio error: {str(e)}")
