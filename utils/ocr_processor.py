"""
OCR Processor for Agricultural AI Advisor
Extracts text from images using multiple OCR methods with agricultural context optimization
"""

# NOTE: Defer heavy OCR imports to runtime to avoid environment conflicts
# (e.g., pandas/numexpr chain when importing pytesseract on some Windows setups)
TESSERACT_AVAILABLE = False
EASYOCR_AVAILABLE = False
TROCR_AVAILABLE = False  # Kept disabled by default for faster startup

import os
import io
import re
import logging
import traceback
import shutil
import requests
from PIL import Image
from PIL import ImageFilter, ImageOps, ImageEnhance
from typing import Dict, List, Optional, Tuple

class OCRProcessor:
    """
    OCR processor optimized for agricultural documents and images
    """
    
    def __init__(self):
        import os  # Explicit import to avoid scoping issues
        self.logger = logging.getLogger(__name__)
        
        # Check for OCR service URL (Docker environment)
        self.ocr_service_url = os.getenv('OCR_SERVICE_URL', 'http://localhost:8898')
        self.use_service = os.getenv('OCR_SERVICE_URL') is not None
        
        if self.use_service:
            self.logger.info(f"OCR service configured at: {self.ocr_service_url}")
        else:
            self.logger.info("Using local OCR engines")
        
        # Enhanced agricultural keywords for fertilizer packages and agricultural products
        self.agricultural_keywords = [
            # Fertilizers and nutrients
            'fertilizer', 'fertiliser', 'urea', 'NPK', 'nitrogen', 'phosphorus', 'potassium',
            'ammonium', 'sulphate', 'sulfate', 'nitrate', 'phosphate', 'potash', 'DAP',
            'compost', 'manure', 'organic', 'bio-fertilizer', 'micronutrient', 'zinc',
            'boron', 'iron', 'manganese', 'copper', 'molybdenum', 'calcium', 'magnesium',
            
            # Pesticides and chemicals
            'pesticide', 'insecticide', 'fungicide', 'herbicide', 'weedicide',
            'spray', 'chemical', 'active', 'ingredient', 'concentration', 'emulsifiable',
            
            # Agricultural general terms
            'seed', 'crop', 'plant', 'soil', 'agriculture', 'farming', 'harvest',
            'irrigation', 'disease', 'insect', 'pest', 'weed', 'treatment',
            'variety', 'hybrid', 'yield', 'growth', 'application', 'dose', 'dosage',
            
            # Measurements and units
            'kg', 'gram', 'gm', 'liter', 'litre', 'ml', 'acre', 'hectare', 'ha',
            'percent', '%', 'ppm', 'temperature', 'humidity', 'pH', 'moisture',
            
            # Package information
            'net', 'weight', 'contents', 'manufactured', 'expiry', 'batch', 'lot',
            'company', 'ltd', 'limited', 'pvt', 'private', 'india', 'brand'
        ]
        
        # Enhanced Hindi agricultural terms for Indian fertilizer packages
        self.hindi_keywords = [
            # Fertilizers
            'खाद', 'उर्वरक', 'यूरिया', 'डीएपी', 'नाइट्रोजन', 'फास्फोरस', 'पोटाश',
            'जैविक', 'रासायनिक', 'कंपोस्ट', 'गोबर', 'खाद',
            
            # Agriculture
            'बीज', 'फसल', 'सिंचाई', 'मिट्टी', 'पौधा', 'रोग', 'कीट', 'खरपतवार',
            'छिड़काव', 'उपचार', 'किस्म', 'उत्पादन', 'पैदावार', 'खेती',
            
            # Measurements
            'एकड़', 'हेक्टेयर', 'किलो', 'ग्राम', 'लीटर', 'मिली', 'प्रतिशत',
            
            # Package terms
            'वजन', 'निर्मित', 'समाप्ति', 'कंपनी', 'प्राइवेट', 'लिमिटेड', 'भारत'
        ]

        # Lazily import OCR libraries only if we need local engines
        global TESSERACT_AVAILABLE, EASYOCR_AVAILABLE, TROCR_AVAILABLE

        if not self.use_service:
            # Try multiple OCR libraries for better compatibility
            try:
                import pytesseract  # type: ignore
                TESSERACT_AVAILABLE = True
                print("INFO: pytesseract available")
                # Store reference for use across methods
                self.pytesseract = pytesseract
            except ImportError:
                TESSERACT_AVAILABLE = False
                print("WARNING: pytesseract not available")

            try:
                import easyocr  # type: ignore
                EASYOCR_AVAILABLE = True
                print("INFO: easyocr available")
            except ImportError:
                EASYOCR_AVAILABLE = False
                print("WARNING: easyocr not available")

            try:
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # type: ignore
                TROCR_AVAILABLE = False  # Temporarily disabled for faster startup
                print("INFO: TrOCR (transformers) temporarily disabled for testing")
            except ImportError:
                TROCR_AVAILABLE = False
                print("WARNING: TrOCR (transformers) not available")

        # Initialize EasyOCR if available
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE:
            try:
                print("INFO: Initializing EasyOCR (this may take a moment for first-time setup)...")
                # Force CPU usage and disable GPU to avoid device conflicts
                import os
                os.environ['CUDA_VISIBLE_DEVICES'] = ''
                import easyocr  # local import after flag set
                self.easyocr_reader = easyocr.Reader(['en', 'hi'], gpu=False, verbose=False)
                print("INFO: EasyOCR initialized successfully with English and Hindi support")
                
            except Exception as e:
                print(f"WARNING: EasyOCR initialization failed: {e}")
                self.easyocr_reader = None
                print(f"WARNING: Full error traceback: {traceback.format_exc()}")
                self.easyocr_reader = None

        # Initialize TrOCR (Microsoft's Transformer OCR)
        self.trocr_processor = None
        if TROCR_AVAILABLE:
            try:
                print("INFO: Initializing TrOCR (Microsoft's Transformer OCR)...")
                import torch
                
                # Set device to CPU explicitly to avoid device mismatch
                device = "cpu"
                
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel  # local import
                self.trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
                self.trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
                
                # Move model to CPU and set to evaluation mode
                self.trocr_model = self.trocr_model.to(device)
                self.trocr_model.eval()
                
                print("INFO: TrOCR initialized successfully - excellent for printed text on packages")
            except Exception as e:
                print(f"WARNING: TrOCR initialization failed: {e}")
                self.trocr_processor = None
                self.trocr_model = None
        else:
            self.trocr_processor = None
            self.trocr_model = None

        # Configure pytesseract to find Tesseract binary on Windows if available
        self.tesseract_configured = False
        if TESSERACT_AVAILABLE:
            try:
                # Respect explicit override if provided
                tess_cmd = os.environ.get('TESSERACT_CMD')
                if tess_cmd and os.path.isfile(tess_cmd):
                    import pytesseract  # local import after flag set
                    # Ensure instance attribute is set
                    self.pytesseract = pytesseract
                    self.pytesseract.pytesseract.tesseract_cmd = tess_cmd
                    self.tesseract_configured = True
                    print(f"INFO: Tesseract configured from TESSERACT_CMD: {tess_cmd}")
                else:
                    # Common install locations
                    common_paths = [
                        r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                        r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                        r"C:\\Users\\{username}\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe".format(username=os.getenv('USERNAME', '')),
                        "tesseract"  # Try PATH
                    ]
                    for p in common_paths:
                        if p == "tesseract":
                            # Check if tesseract is in PATH
                            if shutil.which("tesseract"):
                                import pytesseract  # local import after flag set
                                self.pytesseract = pytesseract
                                self.pytesseract.pytesseract.tesseract_cmd = "tesseract"
                                self.tesseract_configured = True
                                print("INFO: Tesseract found in PATH")
                                break
                        elif os.path.isfile(p):
                            import pytesseract  # local import after flag set
                            self.pytesseract = pytesseract
                            self.pytesseract.pytesseract.tesseract_cmd = p
                            self.tesseract_configured = True
                            print(f"INFO: Tesseract configured: {p}")
                            break
                    
                    if not self.tesseract_configured:
                        print("WARNING: Tesseract executable not found in common locations")
            except Exception as e:
                self.logger.warning(f"Could not configure Tesseract path: {e}")
                print(f"WARNING: Tesseract configuration error: {e}")
        
        # Print OCR status
        self._print_ocr_status()
    
    def _print_ocr_status(self):
        """Print current OCR capabilities status"""
        print("\nINFO: OCR Status:")
        
        if TROCR_AVAILABLE and self.trocr_processor and self.trocr_model:
            print("  INFO: TrOCR (Microsoft Transformer): Ready - BEST for printed text")
        elif TROCR_AVAILABLE:
            print("  WARNING: TrOCR: Available but not initialized")
        else:
            print("  ERROR: TrOCR: Not available")
        
        if EASYOCR_AVAILABLE and self.easyocr_reader:
            print("  INFO: EasyOCR: Ready")
        elif EASYOCR_AVAILABLE:
            print("  WARNING: EasyOCR: Available but not initialized")
        else:
            print("  ERROR: EasyOCR: Not available")
        
        if TESSERACT_AVAILABLE and self.tesseract_configured:
            print("  INFO: Tesseract OCR: Ready")
        elif TESSERACT_AVAILABLE:
            print("  WARNING: Tesseract OCR: Available but not configured")
        else:
            print("  ERROR: Tesseract OCR: Not available")
        
        if not (TROCR_AVAILABLE or EASYOCR_AVAILABLE or TESSERACT_AVAILABLE):
            print("  WARNING: Using fallback OCR methods only")
        print()
    
    def _try_ocr_service(self, image_file) -> Dict:
        """
        Try to use the Docker OCR service for text extraction
        """
        try:
            # Prepare image for service
            files = {'image': image_file}
            response = requests.post(f"{self.ocr_service_url}/extract", files=files, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'text': result.get('text', ''),
                    'cleaned_text': result.get('text', ''),
                    'engine_used': 'ocr-service',
                    'confidence': result.get('confidence', 0.8)
                }
            else:
                self.logger.warning(f"OCR service returned status {response.status_code}")
                return {'success': False, 'error': f"Service error: {response.status_code}"}
                
        except Exception as e:
            self.logger.error(f"OCR service communication failed: {e}")
            return {'success': False, 'error': str(e)}

    def extract_text_from_image(self, image_file, language='eng+hin') -> Dict:
        """
        Extract text from uploaded image file using multiple OCR methods
        
        Args:
            image_file: Streamlit uploaded file object
            language: OCR language (default: English + Hindi)
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            # Try OCR service first if available (Docker environment)
            if self.use_service:
                self.logger.info("Attempting OCR service extraction...")
                service_result = self._try_ocr_service(image_file)
                if service_result.get('success') and service_result.get('cleaned_text'):
                    self.logger.info(f"OCR service succeeded with {len(service_result['cleaned_text'])} characters")
                    return service_result
                else:
                    self.logger.warning("OCR service failed, falling back to local engines")
                    # On-demand enable local Tesseract as last-resort fallback
                    self._ensure_tesseract_setup()
            
            # Fallback to local OCR engines
            # Convert uploaded file to PIL Image
            image = Image.open(image_file)
            
            # Preprocess image for better OCR results
            processed_image = self._preprocess_image(image)

            # Try multiple OCR methods in order of preference
            results = []
            debug_info = []
            
            print(f"INFO: Starting OCR extraction with {len(self.agricultural_keywords)} agricultural keywords")
            
            # Method 1: Try Pytesseract FIRST (Main OCR method)
            if TESSERACT_AVAILABLE and self.tesseract_configured:
                try:
                    print("INFO: Attempting Tesseract OCR extraction...")
                    tesseract_result = self._try_tesseract_ocr(processed_image, language)
                    debug_info.append(f"Pytesseract: {len(tesseract_result.get('cleaned_text', ''))} chars")
                    
                    if tesseract_result.get('cleaned_text'):
                        results.append(('Pytesseract', tesseract_result))
                        print(f"INFO: Pytesseract succeeded with {len(tesseract_result['cleaned_text'])} characters")
                except Exception as e:
                    print(f"ERROR: Pytesseract OCR failed: {e}")
                    debug_info.append(f"Pytesseract failed: {str(e)}")
                    self.logger.debug(f"Pytesseract OCR failed: {e}")
            else:
                print("INFO: Pytesseract OCR not available or not configured")
                debug_info.append("Pytesseract not available/configured")
            
            # Method 2: Try EasyOCR as backup
            if EASYOCR_AVAILABLE:
                print(f"INFO: EasyOCR available: {EASYOCR_AVAILABLE}")
                print(f"INFO: EasyOCR reader initialized: {self.easyocr_reader is not None}")
                
                if self.easyocr_reader:
                    try:
                        print("INFO: Attempting EasyOCR extraction...")
                        easyocr_result = self._try_easyocr(processed_image)
                        debug_info.append(f"EasyOCR: {len(easyocr_result.get('cleaned_text', ''))} chars")
                        
                        if easyocr_result.get('cleaned_text'):
                            results.append(('EasyOCR', easyocr_result))
                            print(f"INFO: EasyOCR succeeded with {len(easyocr_result['cleaned_text'])} characters")
                        else:
                            print("WARNING: EasyOCR returned empty text")
                    except Exception as e:
                        print(f"ERROR: EasyOCR failed: {e}")
                        debug_info.append(f"EasyOCR failed: {str(e)}")
                        self.logger.debug(f"EasyOCR failed: {e}")
                else:
                    print("WARNING: EasyOCR reader not initialized")
                    debug_info.append("EasyOCR reader not initialized")
            else:
                print("WARNING: EasyOCR not available")
                debug_info.append("EasyOCR not available")

            # Method 3: Try TrOCR as secondary backup
            if TROCR_AVAILABLE and self.trocr_processor and self.trocr_model:
                try:
                    print("INFO: Attempting TrOCR extraction...")
                    trocr_result = self._try_trocr(processed_image)
                    debug_info.append(f"TrOCR: {len(trocr_result.get('cleaned_text', ''))} chars")
                    
                    if trocr_result.get('cleaned_text'):
                        results.append(('TrOCR', trocr_result))
                        print(f"INFO: TrOCR succeeded with {len(trocr_result['cleaned_text'])} characters")
                    else:
                        print("WARNING: TrOCR returned empty text")
                except Exception as e:
                    print(f"ERROR: TrOCR failed: {e}")
                    debug_info.append(f"TrOCR failed: {str(e)}")
                    self.logger.debug(f"TrOCR failed: {e}")
            else:
                print("WARNING: TrOCR not available or not initialized")
                debug_info.append("TrOCR not available/initialized")

            # Method 3: Basic image analysis fallback
            print("INFO: Attempting basic image analysis...")
            fallback_result = self._try_basic_image_analysis(processed_image)
            debug_info.append(f"Basic Analysis: {len(fallback_result.get('cleaned_text', ''))} chars")
            
            if fallback_result.get('cleaned_text'):
                results.append(('Basic Analysis', fallback_result))

            print(f"INFO: OCR methods tried: {len(results)} successful")
            print(f"INFO: Debug info: {'; '.join(debug_info)}")

            # Choose the best result
            if results:
                # Select best result based on priority: Pytesseract > EasyOCR > TrOCR
                def result_priority(item):
                    method, result = item
                    text_length = len(result.get('cleaned_text', ''))
                    confidence = result.get('confidence_score', 0)
                    
                    # NEW Priority: Pytesseract > EasyOCR > TrOCR > Basic Analysis
                    if method == 'Pytesseract':
                        priority = text_length + confidence + 3000  # Highest priority
                    elif method == 'EasyOCR':
                        priority = text_length + confidence + 2000  # Second priority
                    elif method == 'TrOCR':
                        priority = text_length + confidence + 1000  # Third priority
                    else:  # Basic Analysis
                        priority = text_length + confidence  # Basic priority
                    
                    return priority
                
                best_method, best_result = max(results, key=result_priority)
                
                print(f"INFO: Selected OCR method: {best_method}")
                print(f"INFO: Extracted text length: {len(best_result.get('cleaned_text', ''))}")
                
                best_result['ocr_method'] = best_method
                best_result['success'] = True
                best_result['debug_info'] = debug_info
                return best_result
            else:
                return self._get_fallback_result("No OCR method could extract text from the image")
            
        except Exception as e:
            self.logger.error(f"OCR processing error: {str(e)}")
            return self._get_fallback_result(str(e))
    
    def _try_trocr(self, image: Image.Image) -> Dict:
        """Try TrOCR (Microsoft's Transformer OCR) for text extraction - excellent for printed text"""
        try:
            print("INFO: Processing image with TrOCR (Microsoft's Transformer OCR)...")
            
            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Process image with explicit device handling
            import torch
            with torch.no_grad():  # Disable gradient computation for inference
                pixel_values = self.trocr_processor(image, return_tensors="pt").pixel_values
                pixel_values = pixel_values.to("cpu")  # Ensure tensors are on CPU
                
                # Generate text using the model
                generated_ids = self.trocr_model.generate(pixel_values, max_length=50)
                generated_text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Clean the extracted text
            cleaned_text = self._clean_text(generated_text)
            
            print(f"INFO: TrOCR extracted text: '{cleaned_text[:100]}...'")
            
            # Analyze text for agricultural context
            analysis = self._analyze_agricultural_content(cleaned_text)
            
            # Calculate confidence based on text quality and agricultural relevance
            confidence = self._calculate_trocr_confidence(cleaned_text, analysis)
            
            return {
                'raw_text': generated_text,
                'cleaned_text': cleaned_text,
                'word_count': len(cleaned_text.split()) if cleaned_text else 0,
                'agricultural_terms': analysis['agricultural_terms'],
                'detected_numbers': analysis['numbers'],
                'detected_measurements': analysis['measurements'],
                'confidence_score': confidence,
                'suggested_context': analysis['context']
            }
        except Exception as e:
            print(f"WARNING: TrOCR extraction failed: {e}")
            print(f"WARNING: TrOCR error type: {type(e).__name__}")
            self.logger.debug(f"TrOCR extraction failed: {e}")
            return self._get_empty_result()

    def _calculate_trocr_confidence(self, text: str, analysis: Dict) -> float:
        """Calculate confidence score for TrOCR results based on text quality and agricultural relevance"""
        if not text:
            return 0.0
        
        confidence = 0.5  # Base confidence for TrOCR
        
        # Boost confidence for agricultural terms
        if analysis['agricultural_terms']:
            confidence += 0.2 * min(len(analysis['agricultural_terms']), 3)
        
        # Boost confidence for numbers and measurements
        if analysis['numbers']:
            confidence += 0.1
        if analysis['measurements']:
            confidence += 0.1
        
        # Boost confidence for reasonable text length
        word_count = len(text.split())
        if 3 <= word_count <= 50:  # Reasonable range for fertilizer packages
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _try_easyocr(self, image: Image.Image) -> Dict:
        """Try EasyOCR for text extraction with enhanced processing for fertilizer images"""
        try:
            print("INFO: Attempting EasyOCR text extraction...")
            
            # Convert PIL image to numpy array for EasyOCR
            import numpy as np
            image_array = np.array(image)
            
            print(f"INFO: Processing image array shape: {image_array.shape}")
            
            # Run EasyOCR with optimized parameters for fertilizer packages
            results = self.easyocr_reader.readtext(
                image_array,
                detail=1,  # Return detailed results with bounding boxes and confidence
                paragraph=False,  # Don't group into paragraphs initially
                width_ths=0.7,  # Text width threshold
                height_ths=0.7,  # Text height threshold
                decoder='greedy',  # Use greedy decoder for better accuracy
                beamWidth=5,  # Beam width for decoder
                batch_size=1  # Process one image at a time
            )
            
            print(f"INFO: EasyOCR found {len(results)} text regions")
            
            # Extract text from results with improved filtering
            extracted_texts = []
            high_confidence_texts = []
            all_confidences = []
            
            for (bbox, text, confidence) in results:
                all_confidences.append(confidence)
                print(f"INFO: Found text '{text}' with confidence {confidence:.3f}")
                
                # More lenient confidence threshold for fertilizer text
                if confidence > 0.2:  # Lowered threshold for fertilizer packages
                    extracted_texts.append(text.strip())
                    if confidence > 0.5:
                        high_confidence_texts.append(text.strip())
            
            # Combine texts intelligently
            if high_confidence_texts:
                raw_text = ' '.join(high_confidence_texts)
            elif extracted_texts:
                raw_text = ' '.join(extracted_texts)
            else:
                raw_text = ''
            
            cleaned_text = self._clean_text(raw_text)
            
            # Calculate average confidence
            avg_confidence = np.mean(all_confidences) if all_confidences else 0
            
            print(f"INFO: EasyOCR extracted text: '{cleaned_text[:100]}...' (confidence: {avg_confidence:.3f})")
            
            # Analyze text for agricultural context
            analysis = self._analyze_agricultural_content(cleaned_text)
            
            return {
                'raw_text': raw_text,
                'cleaned_text': cleaned_text,
                'word_count': len(cleaned_text.split()) if cleaned_text else 0,
                'agricultural_terms': analysis['agricultural_terms'],
                'detected_numbers': analysis['numbers'],
                'detected_measurements': analysis['measurements'],
                'confidence_score': avg_confidence,
                'suggested_context': analysis['context'],
                'extraction_details': {
                    'total_regions': len(results),
                    'high_confidence_regions': len(high_confidence_texts),
                    'avg_confidence': avg_confidence
                }
            }
        except Exception as e:
            print(f"WARNING: EasyOCR extraction failed: {e}")
            print(f"WARNING: EasyOCR error type: {type(e).__name__}")
            self.logger.debug(f"EasyOCR extraction failed: {e}")
            return self._get_empty_result()

    def _try_tesseract_ocr(self, image: Image.Image, language: str) -> Dict:
        """Try Tesseract OCR for text extraction"""
        try:
            # Try multiple configurations and language fallbacks
            psm_modes = [6, 3, 4, 11, 7]
            oem_modes = [3, 1]
            # Ensure unique language list while preserving order
            lang_candidates: List[str] = []
            for l in [language, 'eng+hin', 'eng', 'hin']:
                if l and l not in lang_candidates:
                    lang_candidates.append(l)

            best = {
                'text': '',
                'clean': '',
                'config': '',
                'lang': ''
            }

            for lang_try in lang_candidates:
                for oem in oem_modes:
                    for psm in psm_modes:
                        cfg = f"--oem {oem} --psm {psm}"
                        text = self._try_ocr(image, lang_try, cfg)
                        clean = self._clean_text(text)
                        if len(clean) > len(best['clean']):
                            best = {'text': text, 'clean': clean, 'config': cfg, 'lang': lang_try}
                # Early exit if we have decent amount of text
                if len(best['clean']) >= 12:
                    break

            # Analyze text for agricultural context
            analysis = self._analyze_agricultural_content(best['clean'])
            
            return {
                'raw_text': best['text'],
                'cleaned_text': best['clean'],
                'word_count': len(best['clean'].split()) if best['clean'] else 0,
                'agricultural_terms': analysis['agricultural_terms'],
                'detected_numbers': analysis['numbers'],
                'detected_measurements': analysis['measurements'],
                'confidence_score': self._calculate_confidence(best['clean']),
                'suggested_context': analysis['context']
            }
        except Exception as e:
            self.logger.debug(f"Tesseract OCR extraction failed: {e}")
            return self._get_empty_result()

    def _try_basic_image_analysis(self, image: Image.Image) -> Dict:
        """Basic image analysis fallback when OCR engines are not available"""
        try:
            # Basic image properties analysis
            width, height = image.size
            mode = image.mode
            
            # Try to detect if image might contain text based on properties
            has_text_indicators = []
            
            # Convert to grayscale for analysis
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # Basic edge detection to see if there are text-like patterns
            import numpy as np
            img_array = np.array(gray_image)
            
            # Simple edge detection
            edges = np.abs(np.diff(img_array, axis=1)).sum()
            text_likelihood = min(edges / (width * height), 1.0)
            
            # Generate basic analysis
            if text_likelihood > 0.1:
                suggested_text = f"Image analysis suggests this may contain text content. Image size: {width}x{height}, Format: {mode}"
                context = "document_analysis"
            else:
                suggested_text = f"Image appears to be primarily visual content. Image size: {width}x{height}, Format: {mode}"
                context = "general"
            
            return {
                'raw_text': suggested_text,
                'cleaned_text': suggested_text,
                'word_count': len(suggested_text.split()),
                'agricultural_terms': [],
                'detected_numbers': [str(width), str(height)],
                'detected_measurements': [],
                'confidence_score': text_likelihood * 0.3,  # Low confidence for fallback
                'suggested_context': context
            }
        except Exception as e:
            self.logger.debug(f"Basic image analysis failed: {e}")
            return self._get_empty_result()

    def _get_empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'raw_text': '',
            'cleaned_text': '',
            'word_count': 0,
            'agricultural_terms': [],
            'detected_numbers': [],
            'detected_measurements': [],
            'confidence_score': 0,
            'suggested_context': 'general'
        }

    def _get_fallback_result(self, error_message: str) -> Dict:
        """
        Return fallback result when OCR is not available
        """
        return {
            'success': False,
            'error': error_message,
            'raw_text': '',
            'cleaned_text': '',
            'word_count': 0,
            'agricultural_terms': [],
            'detected_numbers': [],
            'detected_measurements': [],
            'confidence_score': 0,
            'suggested_context': 'general',
            'fallback': True,
            'ocr_method': 'None'
        }
    
    def _ensure_tesseract_setup(self) -> None:
        """
        Lazily import and configure Tesseract only when needed.
        Safe to call multiple times; it will no-op if already configured.
        """
        try:
            global TESSERACT_AVAILABLE
            if TESSERACT_AVAILABLE and getattr(self, 'tesseract_configured', False):
                return
            try:
                import pytesseract  # type: ignore
                TESSERACT_AVAILABLE = True
                # Ensure instance attribute is set for later use
                self.pytesseract = pytesseract
            except Exception as e:
                self.logger.warning(f"Pytesseract import failed on-demand: {e}")
                TESSERACT_AVAILABLE = False
                return

            # Configure tesseract executable
            if not getattr(self, 'tesseract_configured', False):
                tess_cmd = os.environ.get('TESSERACT_CMD')
                try:
                    if tess_cmd and os.path.isfile(tess_cmd):
                        pytesseract.pytesseract.tesseract_cmd = tess_cmd
                        self.tesseract_configured = True
                        print(f"INFO: On-demand Tesseract configured from TESSERACT_CMD: {tess_cmd}")
                    else:
                        common_paths = [
                            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
                            r"C:\\Users\\{username}\\AppData\\Local\\Programs\\Tesseract-OCR\\tesseract.exe".format(username=os.getenv('USERNAME', '')),
                            "tesseract"
                        ]
                        for p in common_paths:
                            if p == "tesseract":
                                if shutil.which("tesseract"):
                                    self.pytesseract.pytesseract.tesseract_cmd = "tesseract"
                                    self.tesseract_configured = True
                                    print("INFO: On-demand Tesseract found in PATH")
                                    break
                            elif os.path.isfile(p):
                                self.pytesseract.pytesseract.tesseract_cmd = p
                                self.tesseract_configured = True
                                print(f"INFO: On-demand Tesseract configured: {p}")
                                break
                        if not getattr(self, 'tesseract_configured', False):
                            print("WARNING: On-demand Tesseract executable not found")
                except Exception as e:
                    self.logger.warning(f"On-demand Tesseract configuration error: {e}")
        except Exception:
            # Never fail caller due to lazy setup
            self.logger.debug(f"_ensure_tesseract_setup error: {traceback.format_exc()}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR results, optimized for fertilizer packages
        """
        try:
            # Store original for fallback
            original_image = image.copy()
            
            # Convert to RGB first if needed (EasyOCR works better with RGB)
            if image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')

            # Resize: upscale images to optimal size for OCR
            width, height = image.size
            min_target = 1000  # Increased for better text recognition
            max_target = 2000  # Prevent excessive memory usage
            
            if width < min_target or height < min_target:
                scale_factor = max(min_target/width, min_target/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            elif width > max_target or height > max_target:
                scale_factor = min(max_target/width, max_target/height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Enhanced preprocessing for fertilizer packages
            if image.mode == 'RGB':
                # Convert to grayscale for processing
                gray_image = image.convert('L')
                
                # Enhance contrast specifically for text on fertilizer packages
                gray_image = ImageOps.autocontrast(gray_image, cutoff=2)
                
                # Apply adaptive sharpening
                gray_image = gray_image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=200, threshold=2))
                
                # Apply slight gaussian blur to reduce noise, then sharpen
                gray_image = gray_image.filter(ImageFilter.GaussianBlur(radius=0.5))
                gray_image = gray_image.filter(ImageFilter.SHARPEN)
                
                # Return RGB version for EasyOCR (convert back to RGB)
                return gray_image.convert('RGB')
            else:
                # For grayscale images
                image = ImageOps.autocontrast(image, cutoff=2)
                image = image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=200, threshold=2))
                return image.convert('RGB')  # EasyOCR prefers RGB
        
        except Exception as e:
            self.logger.error(f"Image preprocessing error: {str(e)}")
            # Return original image converted to RGB as fallback
            try:
                return original_image.convert('RGB')
            except:
                return original_image

    def _try_ocr(self, image: Image.Image, language: str, config: str) -> str:
        """
        Attempt OCR with given language and config, capturing errors.
        """
        try:
            # Use instance-bound pytesseract to ensure availability after lazy import
            return self.pytesseract.image_to_string(image, lang=language, config=config)
        except Exception as e:
            # Log once per unique config to avoid noise
            self.logger.debug(f"OCR try failed (lang={language}, cfg='{config}'): {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters that might be OCR artifacts
        text = re.sub(r'[^\w\s\.\,\-\:\;\(\)\%\/]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _analyze_agricultural_content(self, text: str) -> Dict:
        """
        Analyze text for agricultural context and terms
        """
        text_lower = text.lower()
        
        # Find agricultural terms
        found_terms = []
        for term in self.agricultural_keywords + self.hindi_keywords:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        # Extract numbers and measurements
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        measurements = re.findall(r'\d+(?:\.\d+)?\s*(?:kg|gram|liter|ml|acre|hectare|%)', text_lower)
        
        # Determine context based on found terms
        context = 'general'
        if any(term in text_lower for term in ['fertilizer', 'खाद', 'npk', 'urea']):
            context = 'fertilizer'
        elif any(term in text_lower for term in ['pesticide', 'spray', 'छिड़काव']):
            context = 'pesticide'
        elif any(term in text_lower for term in ['seed', 'बीज', 'variety', 'किस्म']):
            context = 'seeds'
        elif any(term in text_lower for term in ['disease', 'रोग', 'treatment', 'उपचार']):
            context = 'disease_treatment'
        
        return {
            'agricultural_terms': found_terms,
            'numbers': numbers,
            'measurements': measurements,
            'context': context
        }
    
    def _calculate_confidence(self, text: str) -> float:
        """
        Calculate confidence score based on text quality
        """
        if not text:
            return 0.0
        
        # Basic confidence based on text length and readability
        word_count = len(text.split())
        
        # Higher confidence for longer, more structured text
        base_confidence = min(word_count / 20, 1.0) * 60
        
        # Bonus for agricultural terms
        agricultural_bonus = len([term for term in self.agricultural_keywords 
                                if term.lower() in text.lower()]) * 5
        
        # Bonus for numbers and measurements (common in agricultural documents)
        number_bonus = len(re.findall(r'\d+', text)) * 2
        
        total_confidence = min(base_confidence + agricultural_bonus + number_bonus, 100.0)
        
        return round(total_confidence, 1)
    
    def format_ocr_results(self, ocr_result: Dict) -> str:
        """
        Format OCR results for display in the UI
        """
        if not ocr_result['success']:
            if ocr_result.get('fallback'):
                return f"""
## ⚠️ OCR Not Available

**Issue**: {ocr_result['error']}

**Alternative**: You can still:
- Ask questions about the visual content of the image
- Describe what you see in the image in the text area below
- Use the Disease Detection page for plant disease analysis

**Note**: OCR functionality requires Tesseract OCR to be installed on the system.
"""
            else:
                return f"❌ OCR Error: {ocr_result['error']}"
        
        if not ocr_result['cleaned_text']:
            return "📄 No text detected in the image."
        
        result_text = f"""
## 📄 Extracted Text from Image

### 📝 Detected Text:
{ocr_result['cleaned_text']}

### 📊 Analysis:
- **Word Count**: {ocr_result['word_count']} words
- **Confidence**: {ocr_result['confidence_score']}%
- **Context**: {ocr_result['suggested_context'].replace('_', ' ').title()}

"""
        
        if ocr_result['agricultural_terms']:
            result_text += f"""### 🌾 Agricultural Terms Found:
{', '.join(ocr_result['agricultural_terms'][:10])}

"""
        
        if ocr_result['detected_measurements']:
            result_text += f"""### 📏 Measurements Detected:
{', '.join(ocr_result['detected_measurements'])}

"""
        
        return result_text
