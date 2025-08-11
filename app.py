from flask import Flask, request, jsonify, make_response, send_from_directory, render_template
import os
from fastai.vision.all import load_learner
from werkzeug.utils import secure_filename
from pathlib import Path
app = Flask(__name__)

# Load the model
model_path = Path("hammer_model_best.pkl")
upload_dir = Path("uploads")
upload_dir.mkdir(exist_ok=True)

learn = load_learner(model_path)  # Load ONCE at startup
VOCAB = list(learn.dls.vocab)  # e.g. ['hammer', 'none']

def predict_argmax(img_path: Path):
    # MultiCategory: use argmax to force one final label
    pred, _, probs = learn.predict(img_path)
    top_idx = int(probs.argmax())
    return VOCAB[top_idx], {VOCAB[i]: float(probs[i]) for i in range(len(VOCAB))}


@app.route('/')
def home():
    return render_template('index.html')

@app.route("/upload-page")
def upload_page():
    return render_template("upload.html")

@app.route("/upload", methods=["POST", "OPTIONS"])
def upload():
    # ✅ Handle the preflight request
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST")
        return response

    # ✅ Handle actual POST request
    image = request.files.get("image")

    if not image:
        response = jsonify({"message": "❌ No image received"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 400

    response = jsonify({"message": f"✅ Received image: {image.filename}"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
