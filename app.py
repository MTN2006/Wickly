from flask import Flask, request, jsonify, make_response, render_template
import os
from fastai.vision.all import load_learner
from werkzeug.utils import secure_filename
from pathlib import Path
import logging

app = Flask(__name__)

# ---- logging (shows up in Render logs) ----
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# ---- model + uploads ----
model_path = Path("hammer_model_V02.pkl")
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

# Force CPU on Render
learn = load_learner(model_path, cpu=True)   # <— key change
VOCAB = list(learn.dls.vocab)                # e.g. ['hammer','none']

def predict_argmax(img_path: Path):
    # MultiCategory: use argmax to force one final label
    _, _, probs = learn.predict(img_path)
    top_idx = int(probs.argmax())
    label = VOCAB[top_idx]
    probs_dict = {VOCAB[i]: float(probs[i]) for i in range(len(VOCAB))}
    return label, probs_dict

# ---- routes ----
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

@app.route('/health')
def health():
    return jsonify({"ok": True, "vocab": VOCAB})

@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload():
    # CORS preflight
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    # Actual POST
    image = request.files.get('image')
    app.logger.info(f"content_type={request.content_type}, files={list(request.files.keys())}")

    if not image:
        response = jsonify({"message": "❌ No image received"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400

    # Save the file
    fname = secure_filename(image.filename or 'upload.png')
    save_path = upload_dir / fname
    image.save(save_path)
    app.logger.info(f"saved to {save_path}")

    # Run prediction
    label, probs = predict_argmax(save_path)
    app.logger.info(f"prediction={label}, probs={probs}")

    # Respond
    response = jsonify({
        "prediction": label,
        "probabilities": probs
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)