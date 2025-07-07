# # from flask import Flask, request, jsonify
# # from flask_cors import CORS
# # from osint_service import run_osint
# # import os

# # app = Flask(__name__)
# # CORS(app)

# # @app.route('/')
# # def home():
# #     return "Flask is up and running"

# # # if __name__ == '__main__':
# # #     app.run(port=800)

# # @app.route("/osint", methods=["POST"])
# # def osint():
# #     data = request.json
# #     name = data.get("name")
# #     city = data.get("city")
# #     extras = data.get("extras", [])

# #     if not name or not city:
# #         return jsonify({"error": "name and city required"}), 400

# #     try:
# #         results = run_osint(name, city, extras)
# #         return jsonify({"results": results})
# #     except Exception as e:
# #         print(f"Error: {e}")
# #         return jsonify({"error": str(e)}), 500

# # if __name__ == "__main__":
# #     import os
# #     port = int(os.environ.get("PORT", 6969))
# #     app.run(host="0.0.0.0", port=port)

# # from flask import Flask, request, jsonify
# # from flask_cors import CORS
# # from osint_service import run_osint
# # import os
# # import json
# # from datetime import datetime

# # app = Flask(__name__)
# # CORS(app)

# # @app.route('/')
# # def home():
# #     return "Flask is up and running 💻✨"

# # @app.route("/osint", methods=["POST"])
# # def osint():
# #     data = request.json
# #     name = data.get("name")
# #     city = data.get("city")
# #     extras = data.get("extraTerms", "").split(",")

# #     if not name or not city:
# #         return jsonify({"error": "name and city required"}), 400

# #     try:
# #         results = run_osint(name, city, extras)

# #         # take the best result
# #         top_result = results[0]

# #         formatted = {
# #             "name": name,
# #             "location": city,
# #             "summary": top_result.get("gemini_summary", "No summary found."),
# #             "confidence": "85%",  # You can improve this with actual logic
# #             "lastUpdated": datetime.now().strftime("%Y-%m-%d")
# #         }

# #         return jsonify({"data": formatted})
# #     except Exception as e:
# #         print(f"🔥 Backend Error: {e}")
# #         return jsonify({"error": str(e)}), 500

# # @app.route("/generate-report", methods=["POST"])
# # def generate_report():
# #     data = request.json.get("personData")

# #     if not data:
# #         return jsonify({"error": "Missing person data"}), 400

# #     try:
# #         # Create reports folder if it doesn't exist
# #         os.makedirs("reports", exist_ok=True)

# #         # Create a safe filename using name and timestamp
# #         name = data.get("name", "person").replace(" ", "_")
# #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# #         filename = f"{name}_report_{timestamp}.json"
# #         path = os.path.join("reports", filename)

# #         # Save the file
# #         with open(path, "w") as f:
# #             json.dump(data, f, indent=2)

# #         return jsonify({"reportPath": path})
# #     except Exception as e:
# #         print(f"🔥 Report Error: {e}")
# #         return jsonify({"error": str(e)}), 500

# # if __name__ == "__main__":
# #     port = int(os.environ.get("PORT", 6969))
# #     app.run(host="0.0.0.0", port=port)

# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from osint_service import run_osint
# import os
# import json
# from datetime import datetime
# import threading
# import time

# app = Flask(__name__)
# CORS(app)

# # Global dictionary to store progress for each search
# progress_store = {}

# @app.route('/')
# def home():
#     return "Flask is up and running 💻✨"

# @app.route("/osint", methods=["POST"])
# def osint():
#     data = request.json
#     name = data.get("name")
#     city = data.get("city")
#     extras = data.get("extraTerms", "").split(",")

#     if not name or not city:
#         return jsonify({"error": "name and city required"}), 400

#     # Create a unique search ID
#     search_id = f"{name}_{city}_{int(time.time())}"
    
#     # Initialize progress
#     progress_store[search_id] = {
#         "percentage": 0,
#         "stage": "Initializing search...",
#         "status": "running",
#         "result": None,
#         "error": None
#     }

#     def run_search():
#         try:
#             # Update progress stages
#             progress_store[search_id].update({"percentage": 10, "stage": "Initializing search..."})
#             time.sleep(0.5)  # Small delay to show progress
            
#             progress_store[search_id].update({"percentage": 25, "stage": "Searching LinkedIn profiles..."})
#             time.sleep(0.5)
            
#             progress_store[search_id].update({"percentage": 50, "stage": "Searching news sources..."})
#             time.sleep(0.5)
            
#             progress_store[search_id].update({"percentage": 75, "stage": "Processing with Gemini AI..."})
            
#             # Run the actual OSINT search
#             results = run_osint(name, city, extras)
            
#             progress_store[search_id].update({"percentage": 90, "stage": "Generating summary..."})
#             time.sleep(0.5)

#             # Format the result
#             top_result = results[0]
#             formatted = {
#                 "name": name,
#                 "location": city,
#                 "summary": top_result.get("gemini_summary", "No summary found."),
#                 "confidence": "85%",
#                 "lastUpdated": datetime.now().strftime("%Y-%m-%d")
#             }

#             progress_store[search_id].update({
#                 "percentage": 100,
#                 "stage": "Complete!",
#                 "status": "completed",
#                 "result": formatted
#             })

#         except Exception as e:
#             progress_store[search_id].update({
#                 "percentage": 0,
#                 "stage": "Search failed",
#                 "status": "error",
#                 "error": str(e)
#             })
#             print(f"🔥 Backend Error: {e}")

#     # Start the search in a separate thread
#     thread = threading.Thread(target=run_search)
#     thread.start()

#     return jsonify({"searchId": search_id})

# @app.route("/progress/<search_id>", methods=["GET"])
# def get_progress(search_id):
#     if search_id not in progress_store:
#         return jsonify({"error": "Search ID not found"}), 404
    
#     return jsonify(progress_store[search_id])

# @app.route("/generate-report", methods=["POST"])
# def generate_report():
#     data = request.json.get("personData")

#     if not data:
#         return jsonify({"error": "Missing person data"}), 400

#     try:
#         # Create reports folder if it doesn't exist
#         os.makedirs("reports", exist_ok=True)

#         # Create a safe filename using name and timestamp
#         name = data.get("name", "person").replace(" ", "_")
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"{name}_report_{timestamp}.json"
#         path = os.path.join("reports", filename)

#         # Save the file
#         with open(path, "w") as f:
#             json.dump(data, f, indent=2)

#         return jsonify({"reportPath": path})
#     except Exception as e:
#         print(f"🔥 Report Error: {e}")
#         return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 6969))
#     app.run(host="0.0.0.0", port=port)

from flask import Flask, request, jsonify
from flask_cors import CORS
from osint_service import run_osint, run_osint_with_progress
import os
import json
from datetime import datetime
import threading
import time

app = Flask(__name__)
CORS(app, origins=["http://localhost:8080", "https://osint-blue.vercel.app"])

# Global dictionary to store progress for each search
progress_store = {}

# Import the progress store to osint_service
import osint_service
osint_service.progress_store = progress_store

@app.route('/')
def home():
    return "Flask is up and running"

@app.route("/osint", methods=["POST"])
def osint():
    data = request.json
    name = data.get("name")
    city = data.get("city")
    extras = data.get("extraTerms", "").split(",")

    if not name or not city:
        return jsonify({"error": "name and city required"}), 400

    # Create a unique search ID
    search_id = f"{name}_{city}_{int(time.time())}"
    
    # Initialize progress
    progress_store[search_id] = {
        "percentage": 0,
        "stage": "Initializing search...",
        "status": "running",
        "result": None,
        "error": None
    }

    def run_search():
        try:
            # Update progress stages
            progress_store[search_id].update({"percentage": 5, "stage": "Initializing search..."})
            time.sleep(0.3)
            
            progress_store[search_id].update({"percentage": 15, "stage": "Searching LinkedIn profiles..."})
            time.sleep(0.3)
            
            progress_store[search_id].update({"percentage": 35, "stage": "Searching news sources..."})
            time.sleep(0.3)
            
            progress_store[search_id].update({"percentage": 55, "stage": "Collecting general information..."})
            time.sleep(0.3)
            
            progress_store[search_id].update({"percentage": 65, "stage": "Processing search results..."})
            
            # Run the actual OSINT search with progress updates
            results = run_osint_with_progress(name, city, extras, search_id)
            
            progress_store[search_id].update({"percentage": 95, "stage": "Finalizing report..."})
            time.sleep(0.3)

            # Format the result
            top_result = results[0]
            formatted = {
                "name": name,
                "location": city,
                "summary": top_result.get("gemini_summary", "No summary found."),
                "confidence": "85%",
                "lastUpdated": datetime.now().strftime("%Y-%m-%d")
            }

            progress_store[search_id].update({
                "percentage": 100,
                "stage": "Complete!",
                "status": "completed",
                "result": formatted
            })

        except Exception as e:
            progress_store[search_id].update({
                "percentage": 0,
                "stage": "Search failed",
                "status": "error",
                "error": str(e)
            })
            print(f"🔥 Backend Error: {e}")

    # Start the search in a separate thread
    thread = threading.Thread(target=run_search)
    thread.start()

    return jsonify({"searchId": search_id})

@app.route("/progress/<search_id>", methods=["GET"])
def get_progress(search_id):
    if search_id not in progress_store:
        return jsonify({"error": "Search ID not found"}), 404
    
    return jsonify(progress_store[search_id])

@app.route("/generate-report", methods=["POST"])
def generate_report():
    data = request.json.get("personData")

    if not data:
        return jsonify({"error": "Missing person data"}), 400

    try:
        # Create reports folder if it doesn't exist
        os.makedirs("reports", exist_ok=True)

        # Create a safe filename using name and timestamp
        name = data.get("name", "person").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_report_{timestamp}.json"
        path = os.path.join("reports", filename)

        # Save the file
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        return jsonify({"reportPath": path})
    except Exception as e:
        print(f"🔥 Report Error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6969))
    app.run(host="0.0.0.0", port=port)