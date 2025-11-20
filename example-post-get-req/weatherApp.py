from flask import Flask, request, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# mongo_uri = os.environ["MONGODB_URI"]  # make sure this is set
mongo_uri = "mongodb+srv://testuser:test12345@alexacluster.hmpbrep.mongodb.net/?appName=alexaCluster"
client = MongoClient(mongo_uri)

db = client["alexaDB"]                # database name (will be created automatically)
collection = db["weatherState"]       # collection name

@app.route("/weather", methods=["POST"])
def set_weather():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("userId")
    weather_speech = data.get("weatherSpeech")

    if not user_id or not weather_speech:
        return jsonify({"error": "Need userId and weatherSpeech"}), 400

    collection.update_one(
        {"userId": user_id},
        {"$set": {"userId": user_id, "weatherSpeech": weather_speech}},
        upsert=True
    )

    return jsonify({"status": "ok", "userId": user_id, "weatherSpeech": weather_speech}), 200


@app.route("/weather", methods=["GET"])
def get_weather():
    user_id = request.args.get("userId", "default")
    doc = collection.find_one({"userId": user_id})
    if not doc:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "userId": doc["userId"],
        "weatherSpeech": doc["weatherSpeech"]
    }), 200



if __name__ == "__main__":
    # runs on http://localhost:5000
    app.run(host="0.0.0.0", port=8000, debug=True)
