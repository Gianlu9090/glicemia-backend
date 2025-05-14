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

# Serve il form HTML
@app.route("/")
def home():
    return render_template("index.html")

# Riceve e salva le credenziali da form
@app.route("/submit", methods=["POST"])
def submit():
    user_id = request.form["userId"]
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    # Cifratura
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Salvataggio su DynamoDB
    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username_enc,
        "password": password_enc,
        "consent": consent
    })

    return f"Dati salvati per l'utente {user_id}"

# ✅ NUOVO endpoint: restituisce credenziali decifrate dato userId
@app.route("/get_creds", methods=["POST"])
def get_creds():
    user_id = request.form.get("userId")

    # Cerca l'utente in DynamoDB
    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})
    item = response.get("Item")

    if not item:
        return jsonify({"error": "Utente non trovato"}), 404

    # Decifra i dati
    username = f.decrypt(item["username"].encode()).decode()
    password = f.decrypt(item["password"].encode()).decode()

    return jsonify({
        "username": username,
        "password": password
    })

# Avvio del server Flask (solo in locale)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
