from flask import Flask, request, jsonify, make_response, render_template
import os
from fastai.vision.all import load_learner
from werkzeug.utils import secure_filename
from pathlib import Path
import logging
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from pathlib import Path
import io, os, uuid

app = Flask(__name__)

# ---- logging (shows up in Render logs) ----
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# ---- model + uploads ----
model_path = Path("candlestick_model_V04.pkl")
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
@app.route('/home')
def home():
    return render_template('index.html')



@app.route('/upload-page')
def upload_page():
    return render_template('upload.html')

@app.route('/library')
def library():
    return render_template('library.html')

@app.route('/health')
def health():
    return jsonify({"ok": True, "vocab": VOCAB})

TARGET_SIZE = (224, 224)  # <-- set to your model’s input size (change if needed)

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

    # ---- NORMALIZE THE IMAGE (fixes phone photos / HEIC / EXIF / RGBA) ----
    # 1) Sanitize original name for logs only (we'll save as PNG after normalization)
    orig_name = secure_filename(image.filename or f"upload_{uuid.uuid4().hex}")

    try:
        # 2) Open from stream (HEIC works if pillow-heif is available)
        pil = Image.open(image.stream)

        # 3) Fix rotation using EXIF
        pil = ImageOps.exif_transpose(pil)

        # 4) Force 3-channel RGB (avoids RGBA/LA/grayscale issues)
        pil = pil.convert("RGB")

        # 5) Resize to model’s expected size (adjust if your model resizes internally)
        if TARGET_SIZE:
            pil = pil.resize(TARGET_SIZE, Image.BILINEAR)

        # 6) Save as clean PNG to disk (uniform format the model can read)
        stem = Path(orig_name).stem
        norm_path = upload_dir / f"{stem}_{uuid.uuid4().hex}.png"
        pil.save(norm_path, format="PNG", optimize=True)

        app.logger.info(f"normalized and saved to {norm_path}")

    except Exception as e:
        app.logger.exception("Image normalization failed")
        response = jsonify({"message": f"❌ Image processing error: {str(e)}"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400

    # ---- PREDICT ----
    try:
        label, probs = predict_argmax(norm_path)  # your existing API
        app.logger.info(f"prediction={label}, probs={probs}")
    except Exception as e:
        app.logger.exception("Prediction failed")
        response = jsonify({"message": f"❌ Prediction error: {str(e)}"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500

    # ---- RESPOND ----
    response = jsonify({
        "prediction": label,
        "probabilities": probs
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)