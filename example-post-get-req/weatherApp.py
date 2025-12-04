from flask import Flask, request, jsonify
from pymongo import MongoClient

from weatherAppKey import mongo_uri

app = Flask(__name__)

client = MongoClient(mongo_uri)

db = client["alexaDB"]                # database name (will be created automatically)
collection = db["weatherState"]       # collection name

@app.route("/weather", methods=["POST"])
def send_data():
    data = request.get_json(force=True, silent=True) or {}
    user_id = data.get("userId")
    door_status = data.get("doorStatus")
    walk_through_status = data.get("walkThroughStatus")
    indoor_temp = data.get("indoorTemp")
    humidity = data.get("humidity")
    calendar_events = data.get("calendarEvents")

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

    collection.update_one(
        {"userId": user_id},
        {
            "$set": {
                "userId": user_id,
                "doorStatus": door_status,
                "walkThroughStatus": walk_through_status,
                "indoorTemp": indoor_temp,
                "humidity": humidity,
                "calendarEvents": calendar_events,
            }
        },
        upsert=True
    )

    return jsonify({
        "status": "ok",
        "userId": user_id,
        "doorStatus": door_status,
        "walkThroughStatus": walk_through_status,
        "indoorTemp": indoor_temp,
        "humidity": humidity,
        "calendarEvents": calendar_events,
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
        "calendarEvents": doc.get("calendarEvents"),
    }), 200



if __name__ == "__main__":
    # runs on http://localhost:5000
    app.run(host="0.0.0.0", port=8000, debug=True)
