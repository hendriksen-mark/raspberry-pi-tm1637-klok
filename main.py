#!/usr/bin/python3
import argparse
import base64
import copy
import json
import logging
import os
import random
import socket
import ssl
import sys
import requests
import uuid
import time
import RPi.GPIO as GPIO
import tm1637
from collections import defaultdict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from subprocess import Popen, check_output, call
from threading import Thread
from time import sleep, strftime
from urllib.parse import parse_qs, urlparse
from functions.network import getIpAddress

brightness = float(0)
pref_bri = float(0)
pref_currenttime = int()
pref_ShowDoublepoint = int()
Display = tm1637.TM1637(23,24)

ap = argparse.ArgumentParser()

# Arguements can also be passed as Environment Variables.
ap.add_argument("--ip", help="The IP address of the host system", type=str)
ap.add_argument("--http-port", help="The port to listen on for HTTP", type=int)
ap.add_argument("--mac", help="The MAC address of the host system", type=str)
ap.add_argument("--no-serve-https", action='store_true', help="Don't listen on port 443 with SSL")
ap.add_argument("--debug", action='store_true', help="Enables debug output")
ap.add_argument("--docker", action='store_true', help="Enables setup for use in docker container")
ap.add_argument("--ip-range", help="Set IP range for light discovery. Format: <START_IP>,<STOP_IP>", type=str)
ap.add_argument("--scan-on-host-ip", action='store_true', help="Scan the local IP address when discovering new lights")
ap.add_argument("--deconz", help="Provide the IP address of your Deconz host. 127.0.0.1 by default.", type=str)
ap.add_argument("--no-link-button", action='store_true', help="DANGEROUS! Don't require the link button to be pressed to pair the Hue app, just allow any app to connect")
ap.add_argument("--disable-online-discover", help="Disable Online and Remote API functions")

args = ap.parse_args()

if args.debug or (os.getenv('DEBUG') and (os.getenv('DEBUG') == "true" or os.getenv('DEBUG') == "True")):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

if args.ip:
    HOST_IP = args.ip
elif os.getenv('IP'):
    HOST_IP = os.getenv('IP')
else:
    HOST_IP = getIpAddress()

if args.http_port:
    HOST_HTTP_PORT = args.http_port
elif os.getenv('HTTP_PORT'):
    HOST_HTTP_PORT = os.getenv('HTTP_PORT')
else:
    HOST_HTTP_PORT = 8000
HOST_HTTPS_PORT = 443 # Hardcoded for now

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
    protocol_version = 'HTTP/1.1'
    server_version = 'nginx'
    sys_version = ''


    def _set_headers(self):

        self.send_response(200)

        mimetypes = {"json": "application/json", "map": "application/json", "html": "text/html", "xml": "application/xml", "js": "text/javascript", "css": "text/css", "png": "image/png"}
        if self.path.endswith((".html",".json",".css",".map",".png",".js", ".xml")):
            self.send_header('Content-type', mimetypes[self.path.split(".")[-1]])
        elif self.path.startswith("/api"):
            self.send_header('Content-type', mimetypes["json"])
        else:
            self.send_header('Content-type', mimetypes["html"])

    def _set_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"Hue\"')
        self.send_header('Content-type', 'text/html')

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
        global bridge_config
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


    def do_PUT(self):
        self._set_headers()
        logging.info("in PUT method")
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        put_dictionary = json.loads(self.data_string.decode('utf8'))
        url_pices = self.path.rstrip('/').split('/')
        logging.info(self.path)
        logging.info(self.data_string)
        for value in len(url_pices):
            logging.info(url_pices[value])

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

def run(https, server_class=ThreadingSimpleServer, handler_class=S):
    if https:
        server_address = ('', HOST_HTTPS_PORT)
        httpd = server_class(server_address, handler_class)
    else:
        server_address = ('', HOST_HTTP_PORT)
        httpd = server_class(server_address, handler_class)
        logging.info('Starting httpd...')
        httpd.serve_forever()
        httpd.server_close()

if __name__ == "__main__":
    try:
        Thread(target=show).start()
        Thread(target=run, args=[False]).start()
        if not args.no_serve_https:
            Thread(target=run, args=[True]).start()
        while True:
            sleep(10)
    except Exception:
        logging.exception("server stopped ")
    finally:
        run_service = False
        #saveConfig()
        logging.info('config saved')
