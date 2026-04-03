from flask import Flask, request, jsonify
from datetime import datetime
app = Flask(__name__)
PORT = 5002

OFFER_TEMPLATE = """
Date: {CURRENT_DATE}
{FIRST_NAME} {LAST_NAME}
{STREET_ADDRESS}
{CITY}, {POSTAL_CODE}
{COUNTRY}

Account Number: {ACCOUNT_NUMBER}

Dear {FIRST_NAME} {LAST_NAME},

As a valued customer, we are pleased to offer you a special financial product designed to support your needs.

You have been pre-approved for the following offer:
Product Type: {OFFER_TYPE}
Credit Limit: ${CREDIT_LIMIT}

This offer is available exclusively to customers with accounts like yours (Account Number: {ACCOUNT_NUMBER}).

If you would like to accept this offer or learn more, please contact us or visit your nearest branch.

We appreciate your continued trust in our bank.

Sincerely,
Customer Relations Team
Your Bank Name
=========================================================
"""


@app.route('/generate', methods=['POST'])
def generate_offer_letter():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON"}), 400

    # Inject current date into the data dictionary
    data['CURRENT_DATE'] = datetime.now().strftime("%B %d, %Y")

    try:
        letter = OFFER_TEMPLATE.format(
            CURRENT_DATE=data.get("CURRENT_DATE", ""),
            FIRST_NAME=data.get("FIRST_NAME", ""),
            LAST_NAME=data.get("LAST_NAME", ""),
            STREET_ADDRESS=data.get("STREET_ADDRESS", ""),
            CITY=data.get("CITY", ""),
            POSTAL_CODE=data.get("POSTAL_CODE", ""),
            COUNTRY=data.get("COUNTRY", ""),
            ACCOUNT_NUMBER=data.get("ACCOUNT_NUMBER", ""),
            OFFER_TYPE=data.get("OFFER_TYPE", ""),
            CREDIT_LIMIT=data.get("CREDIT_LIMIT", "")
        )

        filename = f"/app/output/Offer_{data.get('FIRST_NAME')}_{data.get('LAST_NAME')}_{data.get('ACCOUNT_NUMBER')}.txt"

        with open(filename, "w") as file:
            file.write(letter)

        return jsonify({"status": "success", "message": "Offer letter created"}), 200

    except KeyError as e:
        return jsonify({"error": str(e)}), 400


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "service": "offer"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)