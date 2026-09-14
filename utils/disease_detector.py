import os
import io
import logging
from typing import Dict, Any, Optional, Tuple

import numpy as np
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False
import requests
try:
    import tensorflow as tf
except Exception:
    tf = None
try:
    import torch
    import torch.nn.functional as F
    from torchvision import transforms
except Exception:
    torch = None
    F = None
    transforms = None

class DiseaseDetector:
    """Plant disease detection using trained TensorFlow model (trained_model.h5).

    Returns keys expected by the UI: 'disease_name', 'confidence', 'category'.
    """

    def __init__(self, service_url=None):
        self.model = None
        self.backend: Optional[str] = None  # 'tf' or 'torch'
        self.service_url = service_url
        self.use_service = service_url is not None
        
        if self.use_service:
            logging.info(f"Disease detector configured to use Docker service: {service_url}")
        else:
            logging.info("Disease detector using local model")
        # Class names aligned with main.py
        self.class_names = [
            'Apple___Apple_scab',
            'Apple___Black_rot',
            'Apple___Cedar_apple_rust',
            'Apple___healthy',
            'Blueberry___healthy',
            'Cherry_(including_sour)___Powdery_mildew',
            'Cherry_(including_sour)___healthy',
            'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot',
            'Corn_(maize)___Common_rust_',
            'Corn_(maize)___Northern_Leaf_Blight',
            'Corn_(maize)___healthy',
            'Grape___Black_rot',
            'Grape___Esca_(Black_Measles)',
            'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)',
            'Grape___healthy',
            'Orange___Haunglongbing_(Citrus_greening)',
            'Peach___Bacterial_spot',
            'Peach___healthy',
            'Pepper,_bell___Bacterial_spot',
            'Pepper,_bell___healthy',
            'Potato___Early_blight',
            'Potato___Late_blight',
            'Potato___healthy',
            'Raspberry___healthy',
            'Soybean___healthy',
            'Squash___Powdery_mildew',
            'Strawberry___Leaf_scorch',
            'Strawberry___healthy',
            'Tomato___Bacterial_spot',
            'Tomato___Early_blight',
            'Tomato___Late_blight',
            'Tomato___Leaf_Mold',
            'Tomato___Septoria_leaf_spot',
            'Tomato___Spider_mites Two-spotted_spider_mite',
            'Tomato___Target_Spot',
            'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
            'Tomato___Tomato_mosaic_virus',
            'Tomato___healthy',
        ]
        self.model_loaded = False
        
    def load_model(self, model_path: str = "trained_model.h5") -> bool:
        """Load model from disk using TensorFlow first; fallback to PyTorch if available."""
        try:
            if self.model is not None:
                return True

            # Try TensorFlow .h5 first
            if tf is not None:
                tf_candidates = [
                    model_path,
                    "trained_model.h5",
                    "model.h5",
                    os.path.join("models", "model.h5"),
                ]
                for candidate in tf_candidates:
                    if os.path.exists(candidate) and candidate.endswith(".h5"):
                        # Avoid requiring training-time custom objects
                        self.model = tf.keras.models.load_model(candidate, compile=False)
                        self.model_loaded = True
                        self.backend = "tf"
                        logging.info(f"TensorFlow model loaded from {candidate}")
                        return True

            # Fallback: PyTorch .pt/.pth
            if torch is not None:
                torch_candidates = [
                    "trained_model.pt",
                    "model.pt",
                    "trained_model.pth",
                    "model.pth",
                    os.path.join("models", "model.pt"),
                    os.path.join("models", "model.pth"),
                ]
                for candidate in torch_candidates:
                    if os.path.exists(candidate):
                        try:
                            # Try TorchScript first
                            self.model = torch.jit.load(candidate, map_location="cpu")
                        except Exception:
                            self.model = torch.load(candidate, map_location="cpu")
                        self.model.eval()
                        self.model_loaded = True
                        self.backend = "torch"
                        logging.info(f"PyTorch model loaded from {candidate}")
                        return True

            logging.warning("No compatible model file found for TensorFlow or PyTorch")
            return False
                
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            return False
    
    def preprocess_image(self, image: Image.Image):
        """Preprocess image for the active backend."""
        try:
            image = image.convert("RGB")
            if self.backend == "torch" and transforms is not None:
                tfm = transforms.Compose([
                    transforms.Resize((128, 128)),
                    transforms.ToTensor(),  # 0-1, CHW
                ])
                tensor = tfm(image).unsqueeze(0)  # (1, C, H, W)
                return tensor
            else:
                # Default to TensorFlow/Numpy path
                image = image.resize((128, 128))
                if tf is not None:
                    arr = tf.keras.preprocessing.image.img_to_array(image)
                else:
                    arr = np.asarray(image, dtype=np.float32)
                arr = np.array([arr])  # (1, H, W, C)
                return arr
        except Exception as e:
            logging.error(f"Error preprocessing image: {e}")
            return None
    
    def predict_disease(self, uploaded) -> Dict[str, Any]:
        """Predict plant disease from a Streamlit UploadedFile or PIL.Image.

        Returns dict with keys: disease_name, confidence, category
        """
        try:
            # If local TF/PyTorch unavailable, try external microservice if configured
            service_url = os.getenv("DISEASE_SERVICE_URL")
            if service_url:
                files = {}
                if hasattr(uploaded, "getvalue"):
                    files['image'] = ('image.jpg', uploaded.getvalue(), 'image/jpeg')
                elif isinstance(uploaded, (bytes, bytearray)):
                    files['image'] = ('image.jpg', bytes(uploaded), 'image/jpeg')
                else:
                    # Convert PIL.Image to bytes
                    if isinstance(uploaded, Image.Image):
                        buf = io.BytesIO()
                        uploaded.save(buf, format='JPEG')
                        buf.seek(0)
                        files['image'] = ('image.jpg', buf.read(), 'image/jpeg')
                    else:
                        try:
                            data = uploaded.read()
                        except Exception:
                            data = None
                        if data:
                            files['image'] = ('image.jpg', data, 'image/jpeg')
                if files:
                    resp = requests.post(service_url.rstrip('/') + '/predict', files=files, timeout=15)
                    if resp.ok:
                        return resp.json()
            
            if not self.model_loaded:
                if not self.load_model():
                    return self._get_manual_result()

            # Load PIL image from various inputs
            if isinstance(uploaded, Image.Image):
                pil_img = uploaded
            else:
                try:
                    # Streamlit UploadedFile has getvalue
                    data = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
                except Exception:
                    data = None
                if not data and isinstance(uploaded, (bytes, bytearray)):
                    data = bytes(uploaded)
                if data is None:
                    return {"error": "Unsupported image input"}
                pil_img = Image.open(io.BytesIO(data))

            batch = self.preprocess_image(pil_img)
            if batch is None:
                return {"error": "Failed to preprocess image"}

            # Predict depending on backend
            if self.backend == "torch":
                with torch.no_grad():
                    outputs = self.model(batch)
                    if isinstance(outputs, (list, tuple)):
                        outputs = outputs[0]
                    # Ensure 2D (batch, num_classes)
                    if outputs.ndim == 1:
                        outputs = outputs.unsqueeze(0)
                    probs = F.softmax(outputs, dim=1)
                    prob, idx_tensor = torch.max(probs, dim=1)
                    idx = int(idx_tensor.item())
                    prob = float(prob.item())
            else:
                preds = self.model.predict(batch)
                idx = int(np.argmax(preds, axis=1)[0])
                prob = float(np.max(preds))
            label = self.class_names[idx]

            plant, disease = self._parse_class_name(label)
            simple_name = "healthy" if "healthy" in disease.lower() else disease
            category = self._infer_category(disease)

            return {
                "disease_name": simple_name,
                "confidence": round(prob * 100.0, 2),
                "category": category,
                # Optionally include full context
                "plant": plant,
                "label": label,
            }

        except Exception as e:
            logging.error(f"Error in disease prediction: {e}")
            return {"error": f"Prediction failed: {str(e)}"}
    
    def _predict_via_service(self, image_data) -> Dict:
        """
        Predict disease using Docker service with robust error handling
        """
        try:
            import requests
            import io
            from PIL import Image
            
            # Prepare image for service
            if hasattr(image_data, 'read'):
                # Streamlit uploaded file
                image_data.seek(0)
                files = {'image': ('image.jpg', image_data, 'image/jpeg')}
            else:
                # PIL Image or other format
                if isinstance(image_data, Image.Image):
                    img_bytes = io.BytesIO()
                    image_data.save(img_bytes, format='JPEG')
                    img_bytes.seek(0)
                    files = {'image': ('image.jpg', img_bytes, 'image/jpeg')}
                else:
                    files = {'image': ('image.jpg', image_data, 'image/jpeg')}
            
            # Send request to disease service
            response = requests.post(
                f"{self.service_url}/predict", 
                files=files, 
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Validate response format
                required_keys = ['disease_name', 'confidence', 'category']
                if all(key in result for key in required_keys):
                    logging.info(f"Disease service prediction successful: {result['disease_name']}")
                    return result
                else:
                    missing_keys = [key for key in required_keys if key not in result]
                    return {"error": f"Invalid service response. Missing keys: {missing_keys}"}
            else:
                return {"error": f"Disease service returned HTTP {response.status_code}"}
                
        except Exception as e:
            logging.error(f"Disease service communication failed: {e}")
            return {"error": f"Service communication failed: {str(e)}"}

    def predict_disease(self, image_input) -> Dict:
        """
        Main prediction method with Docker service integration and local fallback
        """
        # Try Docker service first if available
        if self.use_service:
            logging.info("Attempting disease prediction via Docker service...")
            service_result = self._predict_via_service(image_input)
            
            if 'error' not in service_result:
                return service_result
            else:
                logging.warning(f"Service prediction failed: {service_result['error']}")
                logging.info("Falling back to local model...")
        
        # Fallback to local prediction
        return self._predict_local(image_input)
    
    def _predict_local(self, image_input) -> Dict[str, Any]:
        """Local prediction using TensorFlow/PyTorch model"""
        try:
            # Load PIL image from various inputs
            if isinstance(image_input, Image.Image):
                pil_img = image_input
            else:
                try:
                    # Streamlit UploadedFile has getvalue
                    if hasattr(image_input, 'getvalue'):
                        pil_img = Image.open(io.BytesIO(image_input.getvalue()))
                    else:
                        pil_img = Image.open(image_input)
                except Exception as e:
                    logging.error(f"Error loading image: {e}")
                    return self._get_manual_result()

            # Preprocess image
            processed_img = self.preprocess_image(pil_img)
            if processed_img is None:
                return self._get_manual_result()

            # Make prediction
            if self.backend == "torch" and torch is not None:
                with torch.no_grad():
                    outputs = self.model(processed_img)
                    if hasattr(outputs, 'logits'):
                        outputs = outputs.logits
                    probabilities = F.softmax(outputs, dim=1)
                    confidence, predicted_idx = torch.max(probabilities, 1)
                    confidence = confidence.item() * 100
                    predicted_idx = predicted_idx.item()
            else:
                # TensorFlow path
                predictions = self.model.predict(processed_img, verbose=0)
                predicted_idx = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_idx]) * 100

            # Get class name and parse it
            if 0 <= predicted_idx < len(self.class_names):
                class_name = self.class_names[predicted_idx]
                plant, disease = self._parse_class_name(class_name)
                category = self._infer_category(disease)
                
                return {
                    "disease_name": disease,
                    "confidence": confidence,
                    "category": category,
                    "plant_type": plant,
                    "class_name": class_name
                }
            else:
                logging.error(f"Invalid prediction index: {predicted_idx}")
                return self._get_manual_result()
                
        except Exception as e:
            logging.error(f"Error in local prediction: {e}")
            return self._get_manual_result()
    
    def predict(self, image_input) -> Dict[str, Any]:
        """Alias for predict_disease to maintain backward compatibility"""
        return self.predict_disease(image_input)
    
    def _parse_class_name(self, class_name: str) -> Tuple[str, str]:
        """Parse class name to extract plant and disease"""
        try:
            parts = class_name.split('___')
            if len(parts) >= 2:
                plant = parts[0].replace('_', ' ')
                disease = parts[1].replace('_', ' ')
                return plant, disease
            else:
                return class_name, "Unknown"
        except:
            return "Unknown", "Unknown"
    
    def _infer_category(self, disease: str) -> str:
        """Infer disease category from disease name."""
        name = disease.lower()
        if "healthy" in name:
            return "Healthy"
        if any(k in name for k in ["blight", "rust", "mildew", "spot", "scab", "leaf mold"]):
            return "Fungal"
        if "bacterial" in name:
            return "Bacterial"
        if "virus" in name:
            return "Viral"
        return "Unknown"

    def _get_recommendations(self, plant: str, disease: str) -> list:
        """Get recommendations based on disease prediction"""
        if "healthy" in disease.lower():
            return [
                "Continue current care practices",
                "Monitor plant regularly for any changes",
                "Ensure proper watering and nutrition",
                "Maintain good air circulation"
            ]
        else:
            return [
                "Remove affected leaves immediately",
                "Improve air circulation around the plant", 
                "Adjust watering schedule to avoid overwatering",
                "Consider applying appropriate fungicide or pesticide",
                "Monitor other plants for similar symptoms"
            ]
    
    def _get_treatment_advice(self, plant: str, disease: str) -> str:
        """Get treatment advice for the detected disease"""
        if "healthy" in disease.lower():
            return "No treatment needed. Plant appears healthy. Continue regular care."
        
        # Basic treatment advice based on common disease types
        if any(term in disease.lower() for term in ["blight", "spot", "rust", "mildew"]):
            return "This appears to be a fungal disease. Remove affected parts, improve air circulation, and consider copper-based fungicide treatment."
        elif "virus" in disease.lower():
            return "This appears to be a viral infection. Remove affected plants to prevent spread. No chemical treatment available for viruses."
        else:
            return "Consult with local agricultural extension office for specific treatment recommendations."
    
    def _get_manual_result(self) -> Dict[str, Any]:
        """Fallback result when model is unavailable."""
        return {
            "disease_name": "Analysis unavailable",
            "confidence": 0.0,
            "category": "Unknown",
        }
    
    def analyze_plant_health(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze plant health from image data"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Predict disease
            result = self.predict_disease(image)
            
            return result
            
        except Exception as e:
            logging.error(f"Error analyzing plant health: {e}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def get_supported_plants(self) -> list:
        """Get list of supported plant types"""
        plants = set()
        for class_name in self.class_names:
            plant, _ = self._parse_class_name(class_name)
            plants.add(plant)
        return sorted(list(plants))