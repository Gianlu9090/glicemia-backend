from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Chiave di criptazione (devi averla salvata in Render come variabile FERNET_KEY)
fernet_key = os.environ.get("FERNET_KEY").encode()
f = Fernet(fernet_key)

# Connessione a DynamoDB (regione e nome tabella DEVONO essere esatti)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    # Mostra il form di registrazione (index.html)
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    # Controlla che la privacy sia stata accettata
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    # Prendi lo userId dal campo nascosto del form (che Alexa ha passato)
    user_id = request.form.get("userId")
    if not user_id:
        return "Parametro userId mancante nel form.", 400

    username = request.form["username"]
    password = request.form["password"]
    # Se l’utente ha messo il checkbox “consent”, consentirà l’uso anonimo dei dati
    consent = "consent" in request.form

    # Cripta username e password per sicurezza
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Costruisci l’item da salvare in DynamoDB (includendo sempre il userId)
    item = {
        "userId": user_id,
        "username": username,
        "username_enc": username_enc,
        "password": password_enc,
        "consent": consent
    }

    # Se l’utente ha dato il consenso, salva anche i campi aggiuntivi
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

    # Salva l’item in DynamoDB
    DEXCOM_TABLE.put_item(Item=item)

    # Mostra la pagina di conferma
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
  <p>Ora puoi chiudere questa pagina e tornare su Alexa.</p>
</body>
</html>
"""

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    # Prova a leggere l’item corrispondente in DynamoDB
    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})
    if "Item" not in response:
        return jsonify({"error": "Utente non trovato"}), 404

    item = response["Item"]
    # Decripta i campi criptati
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
    # In locale gira su porta 10000, ma in Render questo non viene usato
    app.run(host="0.0.0.0", port=10000)
