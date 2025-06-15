#!/usr/bin/python3
import logging
import os
import tm1637
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from time import sleep

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s'
)

brightness = 0.5  # Default brightness (0.0 - 1.0)
last_brightness = None
last_time = None
last_doublepoint = None
Display = tm1637.TM1637(24, 23)

HOST_IP = os.getenv('IP', '0.0.0.0')
HOST_HTTP_PORT = 8000

logging.info("Using Host %s:%s", HOST_IP, HOST_HTTP_PORT)

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

def set_brightness_from_url(url_parts):
    global brightness
    try:
        # Expecting /Bri/###, take last part as int
        value = int(url_parts[-1])
        # Map 0-100% to steps 0-7 (include 0)
        step = min(7, max(0, round((value / 100) * 7)))
        brightness = step / 7.0
        logging.info(f"Brightness set to step {step}/7 ({brightness:.2f})")
    except Exception as e:
        logging.error(f"Invalid brightness value: {url_parts} ({e})")

def set_power(state):
    global power_state
    power_state = state

class S(BaseHTTPRequestHandler):
    def _set_headers(self, content_type="text/html"):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")

    def _set_end_headers(self, data):
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        global power_state, brightness
        if self.path.startswith("/Bri"):
            self._set_headers("application/json")
            url_parts = self.path.rstrip('/').split('/')
            set_brightness_from_url(url_parts)
            self._set_end_headers(b"done")
        elif self.path == "/on":
            set_power(True)
            self._set_headers("application/json")
            self._set_end_headers(b"on")
        elif self.path == "/off":
            set_power(False)
            self._set_headers("application/json")
            self._set_end_headers(b"off")
        elif self.path == "/status":
            self._set_headers("application/json")
            state = b"on" if power_state else b"off"
            self._set_end_headers(state)
        elif self.path == "/infoBri":
            self._set_headers("application/json")
            bri_percent = int(brightness * 100)
            self._set_end_headers(str(bri_percent).encode())
        else:
            self.send_error(404, 'Not found, set brightness: /Bri/###')

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(server_class=ThreadingSimpleServer, handler_class=S):
    server_address = ('', HOST_HTTP_PORT)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    try:
        Thread(target=show, daemon=True).start()
        Thread(target=run, daemon=True).start()
        while True:
            sleep(10)
    except Exception:
        logging.exception("Server stopped")
