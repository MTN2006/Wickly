from flask import Flask, request, jsonify, make_response, send_from_directory, render_template
import os

app = Flask(__name__)

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
    app.run(host="0.0.0.0", port=10000)
