from flask import Flask, request, jsonify, make_response
import os

app = Flask(__name__)

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
    app.run(debug=True)