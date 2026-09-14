import os
import io
import json
from typing import Dict

from flask import Flask, request, jsonify
from PIL import Image
import numpy as np

# Import TensorFlow only in this isolated service
import tensorflow as tf  # Expected to be installed in this service's venv (e.g., 2.10.0 CPU)

app = Flask(__name__)


# Class names aligned with main.py
CLASS_NAMES = [
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


def parse_class_name(class_name: str):
    parts = class_name.split('___')
    if len(parts) >= 2:
        plant = parts[0].replace('_', ' ')
        disease = parts[1].replace('_', ' ')
        return plant, disease
    return class_name, "Unknown"


def infer_category(disease: str) -> str:
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


MODEL = None


def load_model() -> tf.keras.Model:
    global MODEL
    if MODEL is not None:
        return MODEL

    # Use only trained_model.h5 for consistency
    model_path = "trained_model.h5"
    if os.path.exists(model_path):
        MODEL = tf.keras.models.load_model(model_path, compile=False)
        return MODEL
    raise FileNotFoundError(f"Model file not found: {model_path}")


def preprocess(image: Image.Image) -> np.ndarray:
    image = image.convert("RGB").resize((128, 128))
    arr = tf.keras.preprocessing.image.img_to_array(image)
    return np.array([arr])


@app.route("/health", methods=["GET"])
def health():
    try:
        load_model()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/predict", methods=["POST"])
def predict():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
    file = request.files['image']
    img = Image.open(file.stream)

    model = load_model()
    batch = preprocess(img)
    preds = model.predict(batch)
    idx = int(np.argmax(preds, axis=1)[0])
    prob = float(np.max(preds))
    label = CLASS_NAMES[idx]
    plant, disease = parse_class_name(label)
    simple = "healthy" if "healthy" in disease.lower() else disease
    category = infer_category(disease)

    return jsonify({
        "disease_name": simple,
        "confidence": round(prob * 100.0, 2),
        "category": category,
        "plant": plant,
        "label": label,
    })


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 8899))
    print(f"Starting Disease Service on port {port}")
    # Use 0.0.0.0 for Docker container accessibility
    app.run(host="0.0.0.0", port=port)
