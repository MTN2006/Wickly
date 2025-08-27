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
# pip install fastai pillow pillow-heif
from fastai.vision.all import *
from io import BytesIO
import pillow_heif  # enables HEIC/HEIF via PIL
pillow_heif.register_heif_opener()

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
@app.route('/')
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


@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload():
    if request.method == 'OPTIONS':
        r = make_response()
        r.headers.add('Access-Control-Allow-Origin', '*')
        r.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        r.headers.add('Access-Control-Allow-Methods', 'POST')
        return r

    f = request.files.get('image')
    if not f:
        r = jsonify({"message":"❌ No image received"})
        r.headers.add("Access-Control-Allow-Origin","*")
        return r, 400

    try:
        # 1) Load from stream (HEIC works because of pillow-heif)
        pil = Image.open(f.stream)
        # 2) Fix EXIF rotation
        pil = ImageOps.exif_transpose(pil)
        # 3) Force 3-channel RGB (removes alpha/LA/gray issues)
        pil = pil.convert("RGB")

        # ✅ Do NOT resize/normalize here. Let fastai handle it.
        pred_class, pred_idx, probs = learn.predict(pil)

        top5 = sorted(
            [{"label": l, "p": float(p)} for l, p in zip(learn.dls.vocab, probs.tolist())],
            key=lambda x: x["p"],
            reverse=True
        )[:5]


                # safest way to pick index + confidence
        topi = int(probs.argmax().item())

        r = jsonify({
            "prediction": str(pred_class),    # e.g. "hammer"
            "index": topi,                    # e.g. 0
            "confidence": float(probs[topi]), # e.g. 0.8
            "top5": top5                      # list of top-5 probs
        })
        r.headers.add("Access-Control-Allow-Origin","*")
        return r, 200

    except Exception as e:
        app.logger.exception("Prediction failed")
        r = jsonify({"message": f"❌ Prediction error: {e}"})
        r.headers.add("Access-Control-Allow-Origin","*")
        return r, 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)