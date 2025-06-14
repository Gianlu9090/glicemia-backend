from flask import Flask, request, render_template, abort, jsonify
import boto3
from cryptography.fernet import Fernet
import os

app = Flask(__name__, template_folder="templates")

# ---------- CONFIG ----------
fernet_key = os.environ.get("FERNET_KEY")
if not fernet_key:
    raise RuntimeError("Devi impostare la variabile d'ambiente FERNET_KEY")
f = Fernet(fernet_key.encode())

dynamodb      = boto3.resource("dynamodb", region_name="us-east-1")
DEXCOM_TABLE  = dynamodb.Table("DexcomUsers")
# --------------------------------

# ======== HOME (form) =========
@app.route("/")
def home():
    """
    Mostra il form di collegamento.
    L'URL *deve* contenere ?userId=<amzn1.ask.account...>
    """
    user_id = request.args.get("userId")
    if not user_id:
        abort(400, description="Richiesta non valida: manca userId nella URL.")

    return render_template("index.html", user_id=user_id)
# ==============================

# ======== SUBMIT (POST) ========
@app.route("/submit", methods=["POST"])
def submit():
    # 1. Privacy obbligatoria
    if "privacy" not in request.form:
        return "Devi accettare la privacy policy per continuare.", 400

    # 2. userId
    user_id = request.form.get("userId")
    if not user_id:
        return "Parametro userId mancante nel form.", 400

    # 3. Credenziali Dexcom
    username = request.form["username"]
    password = request.form["password"]
    consent  = "consent" in request.form

    # 4. Cifra
    item = {
        "userId":       user_id,
        "username_enc": f.encrypt(username.encode()).decode(),
        "password":     f.encrypt(password.encode()).decode(),
        "consent":      consent
    }

    # 5. Facoltativi se c’è consenso
    if consent:
        if request.form.get("birth_year"):
            try:
                item["birth_year"] = int(request.form["birth_year"])
            except ValueError:
                pass
        if request.form.get("gender"):
            item["gender"] = request.form["gender"]
        if request.form.get("diabetes_type"):
            item["diabetes_type"] = request.form["diabetes_type"]

    # 6. Log & salvataggio
    print(f"[DEBUG] submit: salvo userId = {user_id}")
    DEXCOM_TABLE.put_item(Item=item)

    # 7. Pagina di conferma
    return render_template("success.html")
# ==============================

# ======== API per la Lambda ========
@app.route("/get_user", methods=["GET"])
def get_user():
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"error": "Parametro userId mancante"}), 400

    print(f"[DEBUG] get_user: userId = {user_id}")
    try:
        resp = DEXCOM_TABLE.get_item(Key={"userId": user_id})
    except Exception as e:
        print(f"[DEBUG] get_user: errore DynamoDB = {e}")
        return jsonify({"error": "Errore interno"}), 500

    if "Item" not in resp:
        return jsonify({"error": "Utente non trovato"}), 404

    item = resp["Item"]
    try:
        username = f.decrypt(item["username_enc"].encode()).decode()
        password = f.decrypt(item["password"].encode()).decode()
    except Exception as e:
        print(f"[DEBUG] get_user: errore decrittazione = {e}")
        return jsonify({"error": "Errore decrittazione"}), 500

    return jsonify({
        "username":      username,
        "password":      password,
        "birth_year":    item.get("birth_year"),
        "gender":        item.get("gender"),
        "diabetes_type": item.get("diabetes_type"),
        "consent":       item.get("consent", False)
    }), 200
# ====================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
