import requests
from datetime import datetime
import json
import logging
import os
# The dotenv library is used to load environment variables from a .env file
from dotenv import load_dotenv

# Load variables from the parent directory's .env file
load_dotenv("../env") 

from flask import Flask, request, jsonify
from pymongo import MongoClient

# Assuming weatherAppKey.py contains the mongo_uri string
from weatherAppKey import mongo_uri

app = Flask(__name__)
# Set logging level for the application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = MongoClient(mongo_uri)

db = client["alexaDB"]                # MongoDB database name
collection = db["weatherState"]       # MongoDB collection name

# --- ALEXA AUTHENTICATION CONFIGURATION ---
# IMPORTANT: The scope and Client ID/Secret must be correct for the Messaging API
ALEXA_CLIENT_ID = os.getenv("ALEXA_CLIENT_ID") 
ALEXA_CLIENT_SECRET = os.getenv("ALEXA_CLIENT_SECRET")
ALEXA_ACCESS_TOKEN = None
ALEXA_TOKEN_EXPIRY = 0
# NOTE: The target user ID is needed for the messaging URL
TARGET_USER_ID = "amzn1.ask.account.subhon" # REPLACE with the actual Amazon User ID of the customer

def get_alexa_access_token():
    """
    Fetches or refreshes the LWA access token required to call the Alexa API.
    
    CRUCIAL CHANGE: We use the 'alexa::messaging:write' scope for the Messaging API.
    """
    global ALEXA_ACCESS_TOKEN, ALEXA_TOKEN_EXPIRY

    # 1. Check if the cached token is still valid
    if ALEXA_ACCESS_TOKEN and ALEXA_TOKEN_EXPIRY > datetime.now().timestamp():
        return ALEXA_ACCESS_TOKEN 

    token_url = "https://api.amazon.com/auth/o2/token"
    
    # Define the scope for the Messaging API
    data = {
        "grant_type": "client_credentials",
        "client_id": ALEXA_CLIENT_ID,
        "client_secret": ALEXA_CLIENT_SECRET,
        "scope": "alexa::messaging:write" # Use 'messaging:write' for the Messaging API
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        ALEXA_ACCESS_TOKEN = token_data["access_token"]
        # Set expiry time a little early (60 seconds)
        ALEXA_TOKEN_EXPIRY = datetime.now().timestamp() + token_data["expires_in"] - 60 
        logging.info("Successfully refreshed Alexa LWA token.")
        
        return ALEXA_ACCESS_TOKEN

    except requests.exceptions.RequestException as e:
        logging.error(f"LWA Token request failed: {e}")
        return None
    

def send_door_event_message(user_id: str, door_status: str, indoor_temp: str, walk_through_status: str):
    """
    Sends a message to the Alexa Messaging API, which will invoke the skill's Lambda.
    
    CRUCIAL CHANGE: The payload is now a custom message, not a fixed Proactive Event schema.
    """
    token = get_alexa_access_token()
    if not token:
        logging.error("Cannot send message: Failed to retrieve Alexa access token.")
        return False
        
    # Messaging API Endpoint (uses user_id in the URL path)
    api_url = f"https://api.amazonalexa.com/v1/messages/users/{user_id}"

    # Custom payload that your Lambda's messaging_api_handler expects
    custom_message_data = {
      "type": "DOOR_EVENT",
      "doorStatus": door_status,
      "walkThroughStatus": walk_through_status,
      "indoorTemp": indoor_temp,
      "timestamp": datetime.now().isoformat() + "Z"
    }

    # Wrap the custom data in the required Messaging API structure
    payload = {
        "data": custom_message_data
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Messaging API usually returns 202 Accepted on success
        response.raise_for_status() 
        
        if response.status_code == 202:
            logging.info("Successfully sent DOOR_EVENT message to Alexa.")
            return True
        else:
            logging.error(f"Messaging API responded with status {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"Messaging API request failed for user {user_id}: {e}")
        return False

@app.route("/weather", methods=["POST"])
def send_data():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("userId")
    door_status = data.get("doorStatus")
    walk_through_status = data.get("walkThroughStatus")
    indoor_temp = data.get("indoorTemp")
    humidity = data.get("humidity")

    missing_fields = [
        name for name, value in [
            ("userId", user_id),
            ("doorStatus", door_status),
            ("walkThroughStatus", walk_through_status),
            ("indoorTemp", indoor_temp),
            ("humidity", humidity),
        ]
        if value is None or (name == "userId" and not value)
    ]

    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    # 1. Store data in MongoDB
    collection.update_one(
        {"userId": user_id},
        {
            "$set": {
                "userId": user_id,
                "doorStatus": door_status,
                "walkThroughStatus": walk_through_status,
                "indoorTemp": indoor_temp,
                "humidity": humidity,
            }
        },
        upsert=True
    )

    # 2. Push message to Alexa Messaging API (only on status change)
    
    # We define the trigger condition here (e.g., when the door opens)
    if door_status == "Open" and user_id == TARGET_USER_ID:
        
        # Call the new function to send the custom message
        if send_door_event_message(user_id, door_status, str(indoor_temp), walk_through_status):
            logging.info(f"Successfully pushed DOOR_EVENT message to Alexa for user {user_id}")
        else:
            logging.error(f"Failed to push DOOR_EVENT message for user {user_id}")

    # --- END NEW LOGIC ---

    return jsonify({
        "status": "ok",
        "userId": user_id,
        "doorStatus": door_status,
        "walkThroughStatus": walk_through_status,
        "indoorTemp": indoor_temp,
        "humidity": humidity,
    }), 200


@app.route("/weather", methods=["GET"])
def get_data():
    user_id = request.args.get("userId", "default")
    doc = collection.find_one({"userId": user_id})
    if not doc:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "userId": doc["userId"],
        "doorStatus": doc.get("doorStatus"),
        "walkThroughStatus": doc.get("walkThroughStatus"),
        "indoorTemp": doc.get("indoorTemp"),
        "humidity": doc.get("humidity"),
    }), 200



if __name__ == "__main__":
    # runs on http://localhost:5000
    app.run(host="0.0.0.0", port=8000, debug=True)