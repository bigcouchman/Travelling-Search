from flask import Blueprint, Response, request, jsonify
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configure GenAI with API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) # Replace the API key with yours

ai_bp = Blueprint("ai_bp", __name__)

# Set up the model
# Set up separate models with different system roles
MODEL_NAME = "gemini-1.5-flash"

# 🧠 Chatbot Model (tourism expert)
chat_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are a tourism expert who looks forward to showing people famous destinations "
        "around the world. You produce short yet concise responses (preferably 5 to 8 sentences), "
        "and give an exciting and friendly vibe."
    )
)

# 🛫 AI Agent Model (command interpreter) WORK IN PROGRESS
agent_model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=(
        "You are an AI travel assistant that understands commands like "
        "'fly to New York' or 'zoom on Tokyo'. "
        "Respond only with a JSON object like: "
        "{\"action\": \"fly\", \"place\": \"New York\"} "
        "Supported actions: fly, travel, zoom. "
        "DO NOT include any explanation or additional text outside the JSON."
    )
)


# Ask Ai chatbot route.
@ai_bp.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    try:
        response = chat_model.generate_content(prompt)
        return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# ✅ Simple geocoder to turn city names into lat/lon
def geocode_location(place):
    try:
        url = f"https://nominatim.openstreetmap.org/search"
        params = {"q": place, "format": "json"}
        res = requests.get(url, params=params, headers={"User-Agent": "AI-Agent"})
        data = res.json()
        if not data:
            return None, None
        return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print("Geocoding failed:", e)
        return None, None

# Agent AI model route
@ai_bp.route("/agent", methods=["POST"])
def ai_agent():
    data = request.get_json()
    prompt = data.get("message", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    try:
        response = agent_model.generate_content(prompt)
        # Expecting model to return something like: {action: "fly", place: "Tokyo"}
        output = response.text
        print("🔍 AI Raw Output:", output)

        import re
        import json

        # Extract action and place using regex
        match = re.search(r'{.*}', output)
        if match:
            agent_data = json.loads(match.group())

            place = agent_data.get("place")
            action = agent_data.get("action")
            if not place or not action:
                return jsonify({"response": response.text})

            lat, lon = geocode_location(place)
            if lat is None:
                return jsonify({"error": f"Could not find location for {place}"}), 404

            return jsonify({
                "action": action.lower(),
                "place": place,
                "lat": lat,
                "lon": lon
            })
        else:
            return jsonify({"response": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Response streaming route (WIP)
@ai_bp.route("/api/ask-stream", methods=["POST"])
def ask_stream():
    data = request.get_json()
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Prompt is required."}), 400

    def stream():
        try:
            chat = chat_model.start_chat()
            for chunk in chat.send_message(prompt, stream=True):
                yield f"data: {chunk.text}\n\n"
        except Exception as e:
            yield f"data: [Error: {str(e)}]\n\n"

    return Response(stream(), mimetype="text/event-stream")
