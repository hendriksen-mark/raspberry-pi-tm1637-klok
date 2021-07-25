#!/usr/bin/python3
import json
import logging
import os
import sys
import time
import RPi.GPIO as GPIO
import tm1637
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from time import sleep, strftime

brightness = float(0)
pref_bri = float(0)
pref_currenttime = int()
pref_ShowDoublepoint = int()
Display = tm1637.TM1637(23,24)

HOST_IP = os.getenv('IP')
HOST_HTTP_PORT = 8000

logging.info("Using Host %s:%s" % (HOST_IP, HOST_HTTP_PORT))

def scan_for_lights():
    print('scan_for_lights')

def show():
    ShowDoublepoint = False
    global brightness
    global pref_bri
    global pref_currenttime
    global pref_ShowDoublepoint
    while(True):
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        second = now.second
        #timenow = datetime.now().strftime("%H%M")
        #currenttime = [int(timenow[0]), int(timenow[1]), int(timenow[2]), int(timenow[3])]
        currenttime = [ int(hour / 10), hour % 10, int(minute / 10), minute % 10 ]
        if pref_currenttime != currenttime:
            Display.Show(currenttime)
            pref_currenttime = currenttime

        if pref_bri != brightness:
            print("disp.sethelderheid " + str(brightness) )
            print("pref_bri_befor " + str(pref_bri) )
            Display.SetBrightness(brightness)
            pref_bri = brightness
            print("pref_bri_after " + str(pref_bri) )

        if pref_ShowDoublepoint != ShowDoublepoint:
            Display.ShowDoublepoint(ShowDoublepoint)
            pref_ShowDoublepoint = ShowDoublepoint

        time.sleep(0.5)
        ShowDoublepoint = not ShowDoublepoint


def feedback(url):
    global brightness
    print('Bri  ')
    print(len(url))
    brightness = int(url[len(url)-1]) / 100

class S(BaseHTTPRequestHandler):
    def _set_headers(self):

        self.send_response(200)

        mimetypes = {"json": "application/json", "map": "application/json", "html": "text/html", "xml": "application/xml", "js": "text/javascript", "css": "text/css", "png": "image/png"}
        if self.path.endswith((".html",".json",".css",".map",".png",".js", ".xml")):
            self.send_header('Content-type', mimetypes[self.path.split(".")[-1]])
        elif self.path.startswith("/api"):
            self.send_header('Content-type', mimetypes["json"])
        else:
            self.send_header('Content-type', mimetypes["html"])

    def _set_end_headers(self, data):
        self.send_header('Content-Length', len(data))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods',
                         'GET, OPTIONS, POST, PUT, DELETE')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)


    def do_GET(self):
        self.read_http_request_body()

        if self.path.startswith("/scan"):
            self._set_headers()
            scan_for_lights()
            self._set_end_headers(bytes("done", "utf8"))

        elif self.path.startswith("/Bri"):
            self._set_headers()
            url_pices = self.path.rstrip('/').split('/')
            feedback(url_pices)
            self._set_end_headers(bytes("done", "utf8"))

        else:
            url_pices = self.path.rstrip('/').split('/')
            if len(url_pices) < 3:
                #self._set_headers_error()
                logging.info(url_pices)
                self.send_error(404, 'not found, set brightness : /Bri/###')
                return

    def read_http_request_body(self):
        return b"{}" if self.headers['Content-Length'] is None or self.headers[
            'Content-Length'] == '0' else self.rfile.read(int(self.headers['Content-Length']))

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    server_address = ('', HOST_HTTP_PORT)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting httpd...')
    httpd.serve_forever()
    httpd.server_close()

if __name__ == "__main__":
    try:
        Thread(target=show).start()
        Thread(target=run, args=[False]).start()
        while True:
            sleep(10)
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
