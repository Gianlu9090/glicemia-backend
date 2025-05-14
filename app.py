from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os
import uuid

app = Flask(__name__)

# Chiave di cifratura da variabile d'ambiente
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# Connessione DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    # Recupera dati form
    username = request.form["username"]
    password = request.form["password"]
    birth_year = request.form.get("birth_year", "")
    gender = request.form.get("gender", "")
    diabetes_type = request.form.get("diabetes_type", "")
    consent = "consent" in request.form
    privacy = "privacy" in request.form

    # Controllo obbligatorio
    if not privacy:
        return "Devi accettare la privacy policy per continuare.", 400

    # Cifra solo la password
    password_enc = f.encrypt(password.encode()).decode()

    # Genera userId unico
    user_id = str(uuid.uuid4())

    # Salva in DynamoDB
    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username,         # <-- in chiaro
        "password": password_enc,     # <-- cifrata
        "birth_year": birth_year,
        "gender": gender,
        "diabetes_type": diabetes_type,
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
    password_dec = f.decrypt(item["password"].encode()).decode()

    return jsonify({
        "username": item["username"],
        "password": password_dec,
        "birth_year": item.get("birth_year"),
        "gender": item.get("gender"),
        "diabetes_type": item.get("diabetes_type"),
        "consent": item.get("consent", False)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
