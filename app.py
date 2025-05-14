from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Chiave di cifratura
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# Connessione a DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    user_id = request.form["userId"]
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username_enc,
        "password": password_enc,
        "consent": consent
    })

    return f"Dati salvati per l'utente {user_id}"

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "Missing userId"}), 400

    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})
    item = response.get("Item")

    if not item:
        return jsonify({"error": "User not found"}), 404

    try:
        username = f.decrypt(item["username"].encode()).decode()
        password = f.decrypt(item["password"].encode()).decode()
    except Exception:
        return jsonify({"error": "Decryption failed"}), 500

    return jsonify({
        "username": username,
        "password": password
    })
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
