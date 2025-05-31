from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Chiave di crittografia (deve esistere come variabile d'ambiente in Render)
fernet_key = os.environ.get("FERNET_KEY")
if not fernet_key:
    raise RuntimeError("Devi impostare la variabile d'ambiente FERNET_KEY")
f = Fernet(fernet_key.encode())

# Connessione a DynamoDB (regione e nome tabella corretti)
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
DEXCOM_TABLE = dynamodb.Table("DexcomUsers")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submit", methods=["POST"])
def submit():
    # 1) Verifica che la privacy sia stata accettata
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    # 2) Preleva lo userId dal campo nascosto del form
    user_id = request.form.get("userId")
    if not user_id:
        return "Parametro userId mancante nel form.", 400

    # 3) Preleva gli altri campi
    username = request.form["username"]
    password = request.form["password"]
    consent = "consent" in request.form

    # 4) Cripta username e password
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # 5) Costruisci l'oggetto che salverai in DynamoDB
    item = {
        "userId": user_id,
        "username": username,
        "username_enc": username_enc,
        "password": password_enc,
        "consent": consent
    }

    # 6) Se è stato spuntato il consenso, salva anche i campi aggiuntivi
    if consent:
        birth_year = request.form.get("birth_year")
        gender = request.form.get("gender")
        diabetes_type = request.form.get("diabetes_type")
        if birth_year:
            try:
                item["birth_year"] = int(birth_year)
            except ValueError:
                pass  # ignora se non è un numero valido
        if gender:
            item["gender"] = gender
        if diabetes_type:
            item["diabetes_type"] = diabetes_type

    # 7) Log di debug prima di salvare
    print(f"[DEBUG-Backend] submit: userId ricevuto = {user_id}")
    print(f"[DEBUG-Backend] submit: oggetto salvato in DynamoDB = {item}")

    # 8) Salva in DynamoDB
    DEXCOM_TABLE.put_item(Item=item)

    # 9) Risposta di conferma all'utente
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
    # 1) Prendi il parametro userId dalla query string
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    # 2) Log di debug del userId ricevuto
    print(f"[DEBUG-Backend] get_user: userId ricevuto = {user_id}")

    # 3) Prova a recuperare l'item da DynamoDB
    try:
        response = DEXCOM_TABLE.get_item(Key={"userId": user_id})
    except Exception as e:
        print(f"[DEBUG-Backend] get_user: Errore get_item DynamoDB = {e}")
        return jsonify({"error": "Errore interno nella lettura utente"}), 500

    # 4) Log di debug della risposta di DynamoDB
    print(f"[DEBUG-Backend] get_user: DynamoDB get_item response = {response}")

    if "Item" not in response:
        print(f"[DEBUG-Backend] get_user: Nessun item trovato per userId={user_id}")
        return jsonify({"error": "Utente non trovato"}), 404

    item = response["Item"]

    # 5) Decripta username e password
    try:
        username_dec = f.decrypt(item["username_enc"].encode()).decode()
        password_dec = f.decrypt(item["password"].encode()).decode()
    except Exception as e:
        print(f"[DEBUG-Backend] get_user: Errore nella decriptazione = {e}")
        return jsonify({"error": "Errore interno nella decriptazione"}), 500

    # 6) Prepara la risposta JSON
    result = {
        "username": username_dec,
        "password": password_dec,
        "birth_year": item.get("birth_year"),
        "gender": item.get("gender"),
        "diabetes_type": item.get("diabetes_type"),
        "consent": item.get("consent", False)
    }

    # 7) Log di debug prima di rispondere
    print(f"[DEBUG-Backend] get_user: risposta inviata = {result}")

    return jsonify(result), 200

if __name__ == "__main__":
    # Questo vale solo in locale, Render ignora questo blocco per il WSGI
    app.run(host="0.0.0.0", port=10000)
