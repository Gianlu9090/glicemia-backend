from flask import Flask, request, render_template
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Recupera la chiave di cifratura
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
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    # Cifratura
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Salvataggio
    DEXCOM_TABLE.put_item(Item={
        "username": username,  # chiave primaria visibile
        "username_enc": username_enc,
        "password": password_enc,
        "consent": consent
    })

    return f"✅ Credenziali salvate per {username}"

# Avvio server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
