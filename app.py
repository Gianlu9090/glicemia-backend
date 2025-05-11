from flask import Flask, request
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Legge la chiave segreta dalla variabile d'ambiente FERNET_KEY
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# Connessione a DynamoDB nella regione corretta (modifica se serve)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    return "✅ Backend online!"

@app.route("/submit", methods=["POST"])
def submit():
    user_id = request.form["userId"]
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    # Cifratura delle credenziali
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

# ✅ Avvio del server Flask per Render (porta e host obbligatori)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
