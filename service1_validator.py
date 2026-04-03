import os
import re
from decimal import Decimal, InvalidOperation

import certifi
import requests
from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError


DB_NAME = "banking"
COLLECTION_NAME = "customers"

WELCOME_SERVICE_URL = "http://welcome_service:5001/generate"
OFFER_SERVICE_URL = "http://offer_service:5002/generate"

PORT = 5000
ACCOUNT_NUMBER_PATTERN = re.compile(r"^\d{8}$")
ALLOWED_OFFER_TYPES = {
    "credit card": "Credit Card",
    "line of credit": "Line of Credit",
}
REQUIRED_TEXT_FIELDS = {
    "FIRST_NAME": "First name is required.",
    "LAST_NAME": "Last name is required.",
    "STREET_ADDRESS": "Street address is required.",
    "CITY": "City is required.",
    "POSTAL_CODE": "Postal code is required.",
    "COUNTRY": "Country is required.",
}


app = Flask(__name__)
RESET_FIELDS_TO_CLEAR = {
    "is_valid": "",
    "validation_errors": "",
}


def get_mongo_uri():
    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri:
        raise RuntimeError("MONGO_URI must be set.")
    return mongo_uri


def create_mongo_client():
    mongo_uri = get_mongo_uri()
    client_kwargs = {}

    if mongo_uri.startswith("mongodb+srv://"):
        client_kwargs["tlsCAFile"] = certifi.where()

    return MongoClient(mongo_uri, **client_kwargs)


def get_collection():
    client = create_mongo_client()
    return client[DB_NAME][COLLECTION_NAME]


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def validate_customer(customer):
    errors = []

    for field_name, error_message in REQUIRED_TEXT_FIELDS.items():
        if not normalize_text(customer.get(field_name)):
            errors.append(error_message)

    account_number = normalize_text(customer.get("ACCOUNT_NUMBER"))
    if not account_number:
        errors.append("Account number is required.")
    elif not ACCOUNT_NUMBER_PATTERN.fullmatch(account_number):
        errors.append("Account number must be 8")

    letter_type = normalize_text(customer.get("LETTER_TYPE")).lower()
    if letter_type not in {"welcome", "offer"}:
        errors.append("LETTER_TYPE must be either 'welcome' or 'offer'.")

    normalized_offer_type = ""
    if letter_type == "offer":
        offer_type = normalize_text(customer.get("OFFER_TYPE"))
        normalized_offer_type = ALLOWED_OFFER_TYPES.get(offer_type.lower(), "")
        if not normalized_offer_type:
            errors.append("OFFER_TYPE must be 'Credit Card' or 'Line of Credit' for offer letters.")

        credit_limit_value = normalize_text(customer.get("CREDIT_LIMIT"))
        if not credit_limit_value:
            errors.append("CREDIT_LIMIT is required for offer letters.")
        else:
            try:
                if Decimal(credit_limit_value) <= 0:
                    errors.append("CREDIT_LIMIT must be greater than 0.")
            except InvalidOperation:
                errors.append("CREDIT_LIMIT must be a valid number.")

    next_service = "none"
    if not errors:
        next_service = letter_type

    return {
        "errors": errors,
        "next_service": next_service,
    }


def build_update_fields(validation_result):
    return {
        "is_valid": not validation_result["errors"],
        "validation_errors": validation_result["errors"],
    }


def build_trigger_payload(customer, update_fields):
    payload = {}
    for key, value in customer.items():
        if key == "_id":
            continue
        payload[key] = value

    payload.update(update_fields)
    payload["customer_id"] = str(customer["_id"])
    return payload


def trigger_downstream_service(customer, next_service, update_fields):
    if next_service == "none":
        return {"attempted": False, "success": False}

    url = WELCOME_SERVICE_URL if next_service == "welcome" else OFFER_SERVICE_URL
    payload = build_trigger_payload(customer, update_fields)

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        return {"attempted": True, "success": True}
    except requests.RequestException:
        return {"attempted": True, "success": False}


def process_pending_customers():
    collection = get_collection()
    pending_customers = list(
        collection.find({"is_valid": {"$exists": False}})
    )

    summary = {
        "total_checked": len(pending_customers),
        "valid_count": 0,
        "invalid_count": 0,
        "welcome_trigger_attempts": 0,
        "offer_trigger_attempts": 0,
        "trigger_successes": 0,
        "trigger_failures": 0,
    }

    for customer in pending_customers:
        validation_result = validate_customer(customer)
        update_fields = build_update_fields(validation_result)
        next_service = validation_result["next_service"]
        collection.update_one({"_id": customer["_id"]}, {"$set": update_fields})

        if update_fields["is_valid"]:
            summary["valid_count"] += 1
        else:
            summary["invalid_count"] += 1

        if next_service == "welcome":
            summary["welcome_trigger_attempts"] += 1
        elif next_service == "offer":
            summary["offer_trigger_attempts"] += 1

    return summary


def reset_validation_state():
    collection = get_collection()
    result = collection.update_many({}, {"$unset": RESET_FIELDS_TO_CLEAR})

    return {
        "matched_records": result.matched_count,
        "modified_records": result.modified_count,
        "message": "Validation fields were cleared. Existing customer records are ready for re-validation.",
    }


@app.get("/health")
def health_check():
    try:
        client = create_mongo_client()
        client.admin.command("ping")
        return jsonify({"status": "ok", "mongo": "connected"}), 200
    except (RuntimeError, PyMongoError) as exc:
        return jsonify({"status": "error", "mongo": str(exc)}), 500

@app.post("/process")
def process_customers():
    try:
        summary = process_pending_customers()
        return jsonify(summary), 200
    except (RuntimeError, PyMongoError) as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/reset-validation")
def reset_validation():
    try:
        summary = reset_validation_state()
        return jsonify(summary), 200
    except (RuntimeError, PyMongoError) as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
