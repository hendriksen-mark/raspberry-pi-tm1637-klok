#!/usr/bin/python3
import logging
import tm1637
from datetime import datetime
from threading import Thread
from time import sleep
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

brightness = 0.0  # Default brightness (0.0 - 1.0)
last_brightness = None
last_time = None
last_doublepoint = None
Display = tm1637.TM1637(24, 23)

HOST_HTTP_PORT = 8000

power_state = True  # True = on, False = off

def show():
    global brightness, last_brightness, last_time, last_doublepoint, power_state
    doublepoint = False
    while True:
        if not power_state:
            if last_time is not None or last_brightness is not None or last_doublepoint is not None:
                Display.Clear()
                last_time = None
                last_brightness = None
                last_doublepoint = None
            sleep(0.5)
            continue

        now = datetime.now()
        hour, minute = now.hour, now.minute
        current_time = [hour // 10, hour % 10, minute // 10, minute % 10]

        # Update time display only if changed
        if last_time != current_time:
            Display.Show(current_time)
            last_time = current_time

        # Update brightness only if changed
        if last_brightness != brightness:
            Display.SetBrightness(brightness)
            last_brightness = brightness

        # Toggle and update doublepoint every loop
        if last_doublepoint != doublepoint:
            Display.ShowDoublepoint(doublepoint)
            last_doublepoint = doublepoint

        sleep(0.5)
        doublepoint = not doublepoint

def set_brightness_from_url(value: int):
    global brightness
    try:
        # Map 0-100% to steps 0-7 (include 0)
        step = min(7, max(0, round((value / 100) * 7)))
        brightness = step / 7.0
        logging.info(f"Brightness set to step {step}/7 ({brightness:.2f})")
    except Exception as e:
        logging.error(f"Invalid brightness value: {value} ({e})")

def set_power(state):
    global power_state
    power_state = state

@app.route('/<request_type>', defaults={'value': None}, methods=['GET'])
@app.route('/<request_type>/<value>', methods=['GET'])
def handle_request(request_type: str, value: int):
    if value is None:
        value = request.args.get("value")
    logging.info(f"Received request: request_type={request_type}, value={value}")
    if request_type == "Bri":
        set_brightness_from_url(value)
        return jsonify({"status": "done"})
    elif request_type == "on":
        set_power(True)
        return jsonify({"status": "on"})
    elif request_type == "off":
        set_power(False)
        return jsonify({"status": "off"})
    elif request_type == "status":
        state = 1 if power_state else 0
        return str(state)
    elif request_type == "infoBri":
        bri_percent = int(brightness * 100)
        return str(bri_percent)
    else:
        return jsonify({"error": "Not found, set brightness: /Bri/###"}), 404

if __name__ == "__main__":
    try:
        Thread(target=show, daemon=True).start()
        app.run(host='0.0.0.0', port=HOST_HTTP_PORT)
        while True:
            sleep(10)
    except Exception:
        logging.exception("Server stopped")
