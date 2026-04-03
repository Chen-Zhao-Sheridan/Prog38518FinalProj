from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
PORT = 5001

WELCOME_TEMPLATE = """
Date: {CURRENT_DATE}
{FIRST_NAME} {LAST_NAME}
{STREET_ADDRESS}
{CITY}, {POSTAL_CODE}
{COUNTRY}

Account Number: {ACCOUNT_NUMBER}

Dear {FIRST_NAME} {LAST_NAME},

Welcome to our bank!

We are pleased to have you as a valued customer. Your new account has been successfully created and is now ready for use.

If you have any questions regarding your account {ACCOUNT_NUMBER}, please do not hesitate to contact our customer service team.

We look forward to serving your banking needs.

Sincerely,
Customer Relations Team
Your Bank Name
=========================================================
"""


@app.route('/generate', methods=['POST'])
def generate_welcome_letter():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON"}), 400

    data['CURRENT_DATE'] = datetime.now().strftime("%B %d, %Y")

    try:
        letter = WELCOME_TEMPLATE.format(
            CURRENT_DATE=data.get("CURRENT_DATE", ""),
            FIRST_NAME=data.get("FIRST_NAME", ""),
            LAST_NAME=data.get("LAST_NAME", ""),
            STREET_ADDRESS=data.get("STREET_ADDRESS", ""),
            CITY=data.get("CITY", ""),
            POSTAL_CODE=data.get("POSTAL_CODE", ""),
            COUNTRY=data.get("COUNTRY", ""),
            ACCOUNT_NUMBER=data.get("ACCOUNT_NUMBER", "")
        )

        filename = f"/app/output/Welcome_{data.get('FIRST_NAME')}_{data.get('LAST_NAME')}_{data.get('ACCOUNT_NUMBER')}.txt"

        with open(filename, "w") as file:
            file.write(letter)

        return jsonify({"status": "success", "message": "Welcome letter created"}), 200

    except KeyError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "welcome"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)