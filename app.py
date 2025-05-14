from flask import Flask, request, render_template
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Chiave segreta
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    # Verifica accettazione privacy
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    username = request.form["username"]
    password = request.form["password"]
    birth_year = request.form.get("birth_year", "")
    gender = request.form.get("gender", "")
    diabetes_type = request.form.get("diabetes_type", "")
    consent = "consent" in request.form

    # Cifratura
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Genera ID utente univoco
    import uuid
    user_id = str(uuid.uuid4())

    # Salva
    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username_enc,
        "password": password_enc,
        "birth_year": birth_year,
        "gender": gender,
        "diabetes_type": diabetes_type,
        "consent": consent
    })

    return f"Dati salvati per l'utente {user_id}"

# Render host
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
