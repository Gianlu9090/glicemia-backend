from flask import Flask, request
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Leggi la chiave di cifratura da variabile di ambiente
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# Connessione DynamoDB
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

    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username_enc,
        "password": password_enc,
        "consent": consent
    })

    return f"Dati salvati per l'utente {user_id}"
