from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Legge la chiave segreta dalla variabile d'ambiente FERNET_KEY
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

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})

    if "Item" not in response:
        return jsonify({"error": "Utente non trovato"}), 404

    item = response["Item"]
    username_dec = f.decrypt(item["username"].encode()).decode()
    password_dec = f.decrypt(item["password"].encode()).decode()

    return jsonify({
        "username": username_dec,
        "password": password_dec,
        "consent": item.get("consent", False)
    })

# ✅ Flask su Render (porta obbligatoria)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
