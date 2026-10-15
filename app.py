


from flask import Flask, jsonify, send_from_directory
import urllib.request
import json
import re

app = Flask(__name__, static_folder=".")

MONITOR_URL = "http://127.0.0.1:8085/data.json"


def get_sensor_data():
    """Read actual hardware sensor data from Libre Hardware Monitor."""
    try:
        request = urllib.request.Request(
            MONITOR_URL,
            headers={"User-Agent": "LaptopMonitor/1.0"}
        )

        with urllib.request.urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as error:
        print("Sensor connection error:", error)
        return None


def find_sensors(nodes, results):
    """Find temperature sensors recursively."""
    if isinstance(nodes, dict):
        nodes = [nodes]

    if not isinstance(nodes, list):
        return

    for node in nodes:
        if not isinstance(node, dict):
            continue

        sensor_type = str(node.get("Type", "")).lower()
        name = str(node.get("Text", ""))
        value = node.get("Value")

        if sensor_type == "temperature" and value is not None:
            match = re.search(r"-?\d+(?:\.\d+)?", str(value))

            if match:
                try:
                    temp = float(match.group())

                    if -20 <= temp <= 150:
                        results.append({
                            "name": name,
                            "temperature": temp
                        })
                except ValueError:
                    pass

        find_sensors(node.get("Children", []), results)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/status")
def status():
    data = get_sensor_data()

    if data is None:
        return jsonify({
            "available": False,
            "cpu_temperature": None,
            "cpu_usage": None,
            "temperatures": [],
            "message": (
                "Cannot connect to Libre Hardware Monitor. "
                "Check Remote Web Server on port 8085."
            )
        })

    sensors = []
    find_sensors(data, sensors)

    # Select the real CPU temperature sensor.
    cpu_temperature = None

    for sensor in sensors:
        name = sensor["name"].strip().lower()

        if "tctl/tdie" in name:
            cpu_temperature = sensor["temperature"]
            break

    # Fallback: other CPU-specific sensor names.
    if cpu_temperature is None:
        for sensor in sensors:
            name = sensor["name"].strip().lower()

            if (
                "cpu package" in name
                or "cpu die" in name
                or "cpu core" in name
            ):
                cpu_temperature = sensor["temperature"]
                break

    return jsonify({
        "available": True,
        "cpu_temperature": cpu_temperature,
        "cpu_usage": None,
        "temperatures": sensors,
        "message": (
            "Live sensor data received."
            if sensors
            else "No temperature sensors found."
        )
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
