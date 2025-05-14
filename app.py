from flask import Flask, request, render_template, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__)

# Legge la chiave segreta dalla variabile d'ambiente FERNET_KEY
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
    username = request.form.get("username")
    password = request.form.get("password")
    consent = "consent" in request.form
    accepted_privacy = "accept_privacy" in request.form

    gender = request.form.get("gender")
    birth_year = request.form.get("birth_year")
    diabetes_type = request.form.get("diabetes_type")

    # Se non accetta la privacy, blocca tutto
    if not accepted_privacy:
        return "Devi accettare la privacy policy per continuare.", 400

    # Cifratura delle credenziali
    username_enc = f.encrypt(username.encode()).decode()
    password_enc = f.encrypt(password.encode()).decode()

    # Crea una chiave univoca per utente (potresti voler usare email, username, ID generato ecc.)
    import uuid
    user_id = str(uuid.uuid4())

    # Salvataggio su DynamoDB
    DEXCOM_TABLE.put_item(Item={
        "userId": user_id,
        "username": username_enc,
        "password": password_enc,
        "consent": consent,
        "gender": gender,
        "birth_year": birth_year,
        "diabetes_type": diabetes_type
    })

    return f"Dati salvati per l'utente anonimo con ID: {user_id}"

@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")

    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    response = DEXCOM_TABLE.get_item(Key={"userId": user_id})

    if "Item" not in response:
        return jsonify({"error": "Utente non trovato"}), 404

    item = response["Item"]
    username_dec = f.decrypt(item["username"].encode()).decode()
    password_dec = f.decrypt(item["password"].encode()).decode()

    return jsonify({
        "username": username_dec,
        "password": password_dec,
        "consent": item.get("consent", False),
        "gender": item.get("gender"),
        "birth_year": item.get("birth_year"),
        "diabetes_type": item.get("diabetes_type")
    })

# Avvio server Flask
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
