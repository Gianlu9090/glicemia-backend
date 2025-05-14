from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os
import uuid

app = Flask(__name__)

# Chiave segreta
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
    # Obbligatori
    username = request.form["username"]
    password = request.form["password"]
    
    # Controlla che abbia accettato privacy policy
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    # Cifratura credenziali
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Costruisce l’item base
    item = {
        "userId": str(uuid.uuid4()),
        "username": username,
        "username_enc": username_enc,
        "password": password_enc,
    }

    # Se l’utente ha acconsentito
    item["consent"] = "consent" in request.form

    if item["consent"]:
        item["birth_year"] = request.form.get("birth_year", "")
        item["gender"] = request.form.get("gender", "")
        item["diabetes_type"] = request.form.get("diabetes_type", "")

    # Salvataggio su DynamoDB
    DEXCOM_TABLE.put_item(Item=item)

    return f"Dati salvati per l'utente {item['userId']}"

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})

    if "Item" not in response:
        return jsonify({"error": "Utente non trovato"}), 404

    item = response["Item"]
    username_dec = f.decrypt(item["username_enc"].encode()).decode()
    password_dec = f.decrypt(item["password"].encode()).decode()

    return jsonify({
        "username": username_dec,
        "password": password_dec,
        "consent": item.get("consent", False),
        "birth_year": item.get("birth_year", ""),
        "gender": item.get("gender", ""),
        "diabetes_type": item.get("diabetes_type", "")
    })

# Avvio Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
