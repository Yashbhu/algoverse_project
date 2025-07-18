from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from datetime import datetime
import threading
import time
import karein
import osint_service

app = Flask(__name__)
CORS(app) 


progress_store = {}
osint_service.progress_store = progress_store

@app.route('/')
def home():
    return "Flask server is up and running."

@app.route("/osint", methods=["POST"])
def osint():
    data = request.json
    name = data.get("name")
    city = data.get("city")
    extras = data.get("extraTerms", "").split(",")

    if not name:
        return jsonify({"error": "Name is a required field."}), 400

    search_id = f"{name.replace(' ', '_')}_{int(time.time())}"
    progress_store[search_id] = {"percentage": 0, "stage": "Initializing...", "status": "running"}

    def run_search_in_background():
        try:
            final_result = osint_service.run_osint_with_progress(name, city, extras, search_id)
            progress_store[search_id].update({
                "percentage": 100, 
                "stage": "Complete!", 
                "status": "completed", 
                "result": final_result
            })
        except Exception as e:
            error_message = str(e)
            progress_store[search_id].update({
                "status": "error", 
                "error": error_message, 
                "stage": "Failed"
            })
            print(f"🔥 Backend Thread Error for '{search_id}': {error_message}")

    thread = threading.Thread(target=run_search_in_background)
    thread.start()
    return jsonify({"searchId": search_id})

@app.route("/progress/<search_id>", methods=["GET"])
def get_progress(search_id):
    progress = progress_store.get(search_id)
    if not progress:
        return jsonify({"error": "Search ID not found"}), 404
    return jsonify(progress)

@app.route("/generate-report", methods=["POST"])
def generate_report():
    data = request.json.get("personData")
    if not data:
        return jsonify({"error": "Missing person data"}), 400
    try:
        os.makedirs("reports", exist_ok=True)
        name = data.get("name", "person").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_report_{timestamp}.json"
        path = os.path.join("reports", filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"📄 Report generated at: {path}")
        return jsonify({"reportPath": path})
    except Exception as e:
        print(f"🔥 Report Generation Error: {e}")
        return jsonify({"error": f"Failed to generate report: {e}"}), 500

if __name__ == "__main__":
    if not osint_service.model or not osint_service.nlp:
        print("\n🚨 WARNING: Application is starting in a degraded state due to initialization errors.")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
