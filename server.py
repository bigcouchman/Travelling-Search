import asyncio
import websockets
import json
import sqlite3
import requests
import os
from dotenv import load_dotenv
# WORK IN PROGRESS SENSOR DATA WEATHER
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Fetch real-time weather using WeatherAPI
def get_weather(lat, lon):
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={lat},{lon}"
        response = requests.get(url)
        data = response.json()
        temperature = data['current']['temp_c']
        humidity = data['current']['humidity']
        return round(temperature, 2), humidity
    except Exception as e:
        print(f"⚠️ Error fetching weather for ({lat}, {lon}): {e}")
        return None, None

# Stream weather updates for the subscribed landmark
async def stream_weather(websocket, lat, lon, name):
    try:
        print(f"Starting stream for {name} ({lat}, {lon})")
        while True:
            temp, hum = get_weather(lat, lon)
            if temp is not None:
                payload = {
                    "type": "sensor",
                    "landmark": name,
                    "lat": lat,
                    "lng": lon,
                    "temperature": temp,
                    "humidity": hum
                }
                await websocket.send(json.dumps(payload))
            await asyncio.sleep(10)  # Wait before next fetch (adjustable)
    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 Connection closed while streaming {name}")

# 🧭 Main WebSocket handler
async def handle_connection(websocket):
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data["type"] == "subscribe":
                    lat = data["lat"]
                    lng = data["lng"]
                    name = data["name"]
                    await stream_weather(websocket, lat, lng, name)
            except Exception as e:
                print(f"Error handling message: {e}")
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Client disconnected")

# 🧠 Run WebSocket server
async def main():
    async with websockets.serve(handle_connection, "localhost", 8765):
        print("WebSocket server running at ws://localhost:8765")
        await asyncio.Future()  # Run forever

asyncio.run(main())
