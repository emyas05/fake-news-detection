import os, json, numpy as np, joblib, re
from flask import Flask, request, jsonify, render_template
from PIL import Image
import io

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)

import tensorflow as tf
from tensorflow import keras

# ==========================================================
# PATCH KERAS 3 — à faire AVANT tout load_model
# Le modèle cnn_best.h5 a été sauvegardé avec BatchNormalization(renorm=...)
# ce paramètre a été supprimé dans Keras 3. On le retire silencieusement.
# ==========================================================
import keras.src.layers.normalization.batch_normalization as _bn_module
_OriginalBN = _bn_module.BatchNormalization

class _PatchedBN(_OriginalBN):
    def __init__(self, **kwargs):
        kwargs.pop('renorm', None)
        kwargs.pop('renorm_clipping', None)
        kwargs.pop('renorm_momentum', None)
        super().__init__(**kwargs)

_bn_module.BatchNormalization = _PatchedBN
keras.layers.BatchNormalization = _PatchedBN

# ==========================================================
# PATHS
# ==========================================================
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, '..', 'models')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ==========================================================
# CHARGEMENT DES MODÈLES
# ==========================================================
print('Chargement des modeles...')

# ── NLP ────────────────────────────────────────────────────
nlp_model      = joblib.load(os.path.join(MODEL_DIR, 'best_classifier.pkl'))
nlp_vectorizer = joblib.load(os.path.join(MODEL_DIR, 'tfidf_vectorizer.pkl'))
print('  NLP : OK')

# ── Image CNN ──────────────────────────────────────────────
image_model = keras.models.load_model(
    os.path.join(MODEL_DIR, 'cnn_best.h5'),
    compile=False
)

with open(os.path.join(MODEL_DIR, 'class_names.json')) as f:
    idx_to_class = json.load(f)   # {"0": "FAKE", "1": "REAL"}

IMG_SIZE = (64, 64)
print('  Image : OK')
print('Tous les modeles charges. Demarrage Flask...\n')

# ==========================================================
# NLP PREPROCESSING
# ==========================================================
lemmatizer = WordNetLemmatizer()
stop_words  = set(stopwords.words('english'))

def preprocess_text(text):
    if not isinstance(text, str):
        return ''
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'[^a-z ]', ' ', text)
    tokens = text.split()
    tokens = [w for w in tokens if w not in stop_words and len(w) > 2]
    tokens = [lemmatizer.lemmatize(w) for w in tokens]
    return ' '.join(tokens)

# ==========================================================
# ROUTES
# ==========================================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict_text', methods=['POST'])
def predict_text():
    data = request.get_json()

    if not data or 'text' not in data or len(data['text'].strip()) < 10:
        return jsonify({'error': 'Texte trop court (minimum 10 caracteres)'}), 400

    text    = data['text'].strip()
    cleaned = preprocess_text(text)

    features = nlp_vectorizer.transform([cleaned])
    pred     = nlp_model.predict(features)[0]
    label    = 'REAL' if pred == 1 else 'FAKE'

    try:
        proba      = nlp_model.predict_proba(features)[0]
        real_proba = proba[1] * 100
        fake_proba = proba[0] * 100
    except AttributeError:
        # LinearSVC n'a pas predict_proba → decision_function
        score      = float(nlp_model.decision_function(features)[0])
        real_proba = min(50 + score * 15, 99.9) if score > 0 else max(50 + score * 15, 0.1)
        fake_proba = 100 - real_proba

    return jsonify({
        'label'     : label,
        'confidence': round(max(real_proba, fake_proba), 1),
        'real_proba': round(real_proba, 1),
        'fake_proba': round(fake_proba, 1)
    })


@app.route('/predict_image', methods=['POST'])
def predict_image():
    if 'image' not in request.files:
        return jsonify({'error': 'Aucune image envoyee'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide'}), 400

    allowed = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
    ext     = file.filename.rsplit('.', 1)[-1].lower()

    if ext not in allowed:
        return jsonify({'error': 'Format non supporte'}), 400

    img = Image.open(io.BytesIO(file.read())).convert('RGB')
    img = img.resize(IMG_SIZE)

    arr   = np.array(img, dtype=np.float32) / 255.0
    arr   = np.expand_dims(arr, axis=0)                      # (1, 64, 64, 3)

    proba = float(image_model.predict(arr, verbose=0)[0][0]) # sortie sigmoid

    label      = 'REAL' if proba >= 0.5 else 'FAKE'
    real_proba = proba * 100
    fake_proba = (1 - proba) * 100

    return jsonify({
        'label'     : label,
        'confidence': round(max(real_proba, fake_proba), 1),
        'real_proba': round(real_proba, 1),
        'fake_proba': round(fake_proba, 1)
    })


# ==========================================================
# RUN
# ==========================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)
