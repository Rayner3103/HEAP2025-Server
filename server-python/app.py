from flask import Flask, jsonify
from flask_cors import CORS  # ...existing code...

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/test/')
def test():
    return jsonify(message="test")

if __name__ == "__main__":
    app.run(debug=True)