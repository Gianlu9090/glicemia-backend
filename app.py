from flask import Flask, request, render_template
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
