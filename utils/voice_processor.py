import os
import io
import tempfile
import logging
from typing import Optional, Dict, Any
import requests
from groq import Groq
try:
    import speech_recognition as sr
except ImportError:
    sr = None
try:
    from gtts import gTTS
except ImportError:
    gTTS = None

class VoiceProcessor:
    """
    Voice processing for speech-to-text and text-to-speech
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=self.groq_api_key)
        self.recognizer = sr.Recognizer() if sr else None
        self.last_detected_lang_code: Optional[str] = None

    def normalize_lang_code(self, lang: Optional[str]) -> str:
        """Map various language names/variants to gTTS ISO codes (lowercase)."""
        if not lang:
            return "en"
        l = str(lang).strip().lower()
        mapping = {
            # English and variants
            "en": "en", "english": "en", "en-in": "en", "en_us": "en", "en-us": "en",
            # Hindi
            "hi": "hi", "hindi": "hi", "hi-in": "hi",
            # Tamil
            "ta": "ta", "tamil": "ta", "ta-in": "ta",
            # Telugu
            "te": "te", "telugu": "te", "te-in": "te",
            # Bengali
            "bn": "bn", "bengali": "bn", "bangla": "bn", "bn-in": "bn",
            # Marathi, Gujarati, Kannada (optional if enabled in sidebar later)
            "mr": "mr", "marathi": "mr",
            "gu": "gu", "gujarati": "gu",
            "kn": "kn", "kannada": "kn",
            "pa": "pa", "punjabi": "pa",
            "ur": "ur", "urdu": "ur",
            "ml": "ml", "malayalam": "ml",
            "or": "or", "odia": "or", "oriya": "or",
            "as": "as", "assamese": "as",
        }
        return mapping.get(l, l if len(l) == 2 else "en")
        
    def transcribe_audio_groq(self, audio_file_path: str) -> str:
        """Transcribe audio using Groq Whisper API with language auto-detect."""
        try:
            with open(audio_file_path, "rb") as file:
                # Attempt verbose response to capture detected language
                try:
                    verbose = self.groq_client.audio.transcriptions.create(
                        file=(audio_file_path, file.read()),
                        model="whisper-large-v3",
                        response_format="verbose_json",
                    )
                    # Groq SDK may return object with attributes or dict-like
                    detected_text = getattr(verbose, "text", None) or (verbose.get("text") if isinstance(verbose, dict) else None)
                    detected_lang = getattr(verbose, "language", None) or (verbose.get("language") if isinstance(verbose, dict) else None)
                    if detected_lang:
                        self.last_detected_lang_code = detected_lang
                    if detected_text:
                        return detected_text
                except Exception:
                    file.seek(0)
                    # Fallback: plain text without language metadata
                    simple = self.groq_client.audio.transcriptions.create(
                        file=(audio_file_path, file.read()),
                        model="whisper-large-v3",
                        response_format="text",
                    )
                    return simple or ""
        except Exception as e:
            logging.error(f"Groq transcription error: {e}")
            return ""
    
    def transcribe_audio_local(self, audio_file_path: str) -> str:
        """Transcribe audio using local speech recognition"""
        if not self.recognizer or not sr:
            return ""
            
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                # Heuristic language detection fallback
                if text:
                    self.last_detected_lang_code = self.detect_language(text)
                return text or ""
        except Exception as e:
            logging.error(f"Local transcription error: {e}")
            return ""
    
    def transcribe_audio(self, audio_file_path: str, method: str = "groq") -> str:
        """Transcribe audio using specified method"""
        if method == "groq":
            result = self.transcribe_audio_groq(audio_file_path)
            if not result:
                # Fallback to local
                result = self.transcribe_audio_local(audio_file_path)
        else:
            result = self.transcribe_audio_local(audio_file_path)
            if not result:
                # Fallback to Groq
                result = self.transcribe_audio_groq(audio_file_path)
        
        # Final fallback language detection from text when not provided
        if result and not self.last_detected_lang_code:
            try:
                self.last_detected_lang_code = self.detect_language(result)
            except Exception:
                self.last_detected_lang_code = None

        return result or "Transcription failed"

    def speech_to_text(self, audio_input: Any) -> str:
        """Accepts audio bytes/UploadedFile from Streamlit and returns transcription text."""
        try:
            # Extract raw bytes from various possible Streamlit audio input types
            raw_bytes = None
            mime_type = getattr(audio_input, "type", None)

            if hasattr(audio_input, "getvalue"):
                # e.g., Streamlit UploadedFile-like object
                raw_bytes = audio_input.getvalue()
            elif hasattr(audio_input, "read"):
                raw_bytes = audio_input.read()
            elif isinstance(audio_input, (bytes, bytearray)):
                raw_bytes = bytes(audio_input)

            if not raw_bytes:
                return ""

            # Choose file extension based on mime if available
            ext = ".wav"
            if isinstance(mime_type, str):
                if "mp3" in mime_type:
                    ext = ".mp3"
                elif "wav" in mime_type:
                    ext = ".wav"

            # Persist to a temporary file for STT backends
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(raw_bytes)
                temp_path = tmp_file.name

            # Prefer Groq Whisper with local fallback
            text = self.transcribe_audio(temp_path, method="groq")

            # Cleanup
            try:
                os.unlink(temp_path)
            except Exception:
                pass

            return text
        except Exception as e:
            logging.error(f"speech_to_text error: {e}")
            return ""
    
    def text_to_speech(self, text: str, language: str = "en") -> Optional[bytes]:
        """Convert text to speech using gTTS (Windows-safe temp handling)."""
        if not gTTS:
            logging.error("gTTS not available")
            return None

        try:
            lang_code = self.normalize_lang_code(language)
            tts = gTTS(text=text, lang=lang_code, slow=False)

            # Create a closed temp file path (avoid open handle during save on Windows)
            fd, temp_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            tts.save(temp_path)

            with open(temp_path, "rb") as audio_file:
                audio_data = audio_file.read()

            # Best-effort cleanup
            try:
                os.remove(temp_path)
            except Exception:
                pass

            return audio_data

        except Exception as e:
            logging.error(f"Text-to-speech error: {e}")
            return None
    
    def detect_language(self, text: str) -> str:
        """Detect language of text (simplified)"""
        # Simple heuristic language detection
        hindi_chars = set('अआइईउऊएऐओऔकखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसह')
        tamil_chars = set('அஆஇஈஉஊஎஏஐஒஓஔகஙசஞடணதநபமயரலவழளறன')
        
        text_chars = set(text)
        
        if text_chars.intersection(hindi_chars):
            return "hi"
    
    def process_voice_input(self, audio_file_path: str) -> Dict[str, Any]:
        """Process voice input: microphone → transcribe → same language detection"""
        try:
            logging.info("Processing voice input from Chromium microphone...")
            
            # Step 1: Transcribe audio using Groq Whisper (preferred) or local fallback
            transcription = self.transcribe_audio(audio_file_path, method="groq")
            
            if not transcription or transcription == "Transcription failed":
                logging.warning("Primary transcription failed, trying local fallback...")
                transcription = self.transcribe_audio(audio_file_path, method="local")
            
            if not transcription or transcription == "Transcription failed":
                return {
                    'success': False,
                    'error': 'Failed to transcribe audio from microphone',
                    'transcription': '',
                    'detected_language': None,
                    'language_code': 'en'
                }
            
            # Step 2: Detect language from transcribed text
            detected_lang = self.detect_language(transcription)
            
            logging.info(f"Voice processing successful: '{transcription[:50]}...' in {detected_lang}")
            
            return {
                'success': True,
                'transcription': transcription,
                'detected_language': detected_lang,
                'language_code': detected_lang,
                'source': 'chromium_microphone'
            }
            
        except Exception as e:
            logging.error(f"Voice processing error: {e}")
            return {
                'success': False,
                'error': str(e),
                'transcription': '',
                'detected_language': 'en',
                'language_code': 'en'
            }

    def generate_response_audio(self, text: str, language_code: str = None) -> Optional[bytes]:
        """Generate audio response in the same language as detected from input"""
        try:
            # Use detected language or fallback to English
            target_lang = language_code or self.last_detected_lang_code or 'en'
            
            logging.info(f"Generating audio response in language: {target_lang}")
            
            # Generate TTS audio in the same language
            audio_bytes = self.text_to_speech(text, target_lang)
            
            if audio_bytes:
                logging.info(f"Audio response generated successfully in {target_lang}")
                return audio_bytes
            else:
                logging.warning(f"TTS failed for {target_lang}, trying English fallback")
                return self.text_to_speech(text, 'en')
                
        except Exception as e:
            logging.error(f"Audio generation error: {e}")
            return None
    
    def create_voice_response(self, text: str, language: str = "en") -> Optional[bytes]:
        """Create voice response from text"""
        try:
            # Limit text length for TTS
            if len(text) > 500:
                text = text[:500] + "..."
            
            return self.text_to_speech(text, language)
            
        except Exception as e:
            logging.error(f"Voice response creation error: {e}")
            return None
    
    def is_available(self) -> Dict[str, bool]:
        """Check availability of voice processing components"""
        return {
            "groq_whisper": bool(self.groq_api_key),
            "speech_recognition": bool(sr and self.recognizer),
            "text_to_speech": bool(gTTS),
            "overall": bool(self.groq_api_key or (sr and self.recognizer))
        }