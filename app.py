from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os
import uuid

app = Flask(__name__)

# Chiave segreta da variabile d'ambiente
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
    # ✅ Blocco se non accettata privacy
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    user_id = str(uuid.uuid4())
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Dati base sempre salvati
    item = {
        "userId": user_id,
        "username": username,
        "username_enc": username_enc,
        "password": password_enc,
        "consent": consent
    }

    # Dati aggiuntivi solo se consenso
    if consent:
        birth_year = request.form.get("birth_year")
        gender = request.form.get("gender")
        diabetes_type = request.form.get("diabetes_type")
        if birth_year:
            item["birth_year"] = int(birth_year)
        if gender:
            item["gender"] = gender
        if diabetes_type:
            item["diabetes_type"] = diabetes_type

    DEXCOM_TABLE.put_item(Item=item)

    return """
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <title>Registrazione completata</title>
</head>
<body style="font-family: sans-serif; text-align: center; margin-top: 100px;">
  <h1 style="color: green;">✅ Registrazione completata con successo!</h1>
  <p>Grazie per aver collegato il tuo account Dexcom.</p>
</body>
</html>
"""

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
        "birth_year": item.get("birth_year"),
        "gender": item.get("gender"),
        "diabetes_type": item.get("diabetes_type"),
        "consent": item.get("consent", False)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
