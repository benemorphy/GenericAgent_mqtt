"""Launcher for rmqtt_webui.py - ensures env vars are set"""
import os, sys, threading, time

# Ensure project root in path
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

# Set env vars
os.environ.setdefault("MQTT_HOST", "127.0.0.1")
os.environ.setdefault("MQTT_PORT", "1883")
os.environ.setdefault("WEB_PORT", "8100")

from tools.rmqtt_webui import mqtt_loop, run

# Start MQTT thread
t = threading.Thread(target=mqtt_loop, daemon=True)
t.start()
time.sleep(2)

# Start HTTP server
print(f"[start_webui] http://127.0.0.1:{os.environ['WEB_PORT']}")
run(host="127.0.0.1", port=int(os.environ["WEB_PORT"]), server="auto", quiet=True)
