#!/usr/bin/env python3
"""rmqtt Web UI - MQTT Broker 监控面板 (bottle + SSE)"""
import json, os, sys, time, queue, threading, logging, html
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.WARN)

DASH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkYXNoYm9hcmQiLCJjbGllbnRpZCI6ImRhc2hib2FyZCIsInVzZXJuYW1lIjoiZGFzaGJvYXJkIiwicm9sZSI6Im9ic2VydmVyIiwiZXhwIjoxODEwNTM2NjU4LCJpYXQiOjE3NzkwMDA2NTh9.f-sExP344F08kYth49iZhHfS2XhzR0WXZN7qkLOI_O4"

try:
    from bottle import route, run, get, response, request
except ImportError:
    os.system("pip install bottle --quiet")
    from bottle import route, run, get, response, request

from mqtt_bbs.client import BBSClient

BROKER_HOST = os.environ.get("MQTT_HOST", "broker.emqx.io")
BROKER_PORT = int(os.environ.get("MQTT_PORT", "1883"))
WEB_PORT = int(os.environ.get("WEB_PORT", "8100"))
# 公共 broker 无需认证；私有部署可通过环境变量覆写
MQTT_USER = os.environ.get("MQTT_USERNAME", "")
MQTT_PASS = os.environ.get("MQTT_PASSWORD", "")

agents = {}
tasks = {}
log_events = []
sse_clients = []
MAX_LOG = 100

def _broadcast(event, data):
    payload = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    dead = []
    for q in sse_clients:
        try:
            q.put_nowait(payload)
        except:
            dead.append(q)
    for q in dead:
        sse_clients.remove(q)

def _log(level, agent_id, msg):
    t = datetime.now().strftime("%H:%M:%S")
    log_events.append((t, level, agent_id, msg))
    if len(log_events) > MAX_LOG:
        log_events[:50] = []
    _broadcast("log", {"time": t, "level": level, "agent": agent_id, "msg": msg})

def _on_message(topic, payload):
    parts = topic.split("/")
    if len(parts) < 3 or parts[0] != "agent":
        return
    sub, rest = parts[1], parts[2:]
    if sub == "node" and len(rest) >= 2 and rest[1] == "status":
        agent_id = rest[0]
        status = payload if isinstance(payload, str) else payload.get("status", "online")
        agents[agent_id] = {"status": status,
                           "last_seen": datetime.now().strftime("%H:%M:%S")}
        _broadcast("agent_update", {"id": agent_id, "status": agents[agent_id]["status"]})
    elif sub in ("board", "task") and len(rest) >= 1 and isinstance(payload, dict):
        task_id = rest[0]
        if task_id not in tasks:
            tasks[task_id] = {"task_id": task_id}
        tasks[task_id]["updated_at"] = datetime.now().strftime("%H:%M:%S")
        if len(rest) >= 2:
            tasks[task_id][rest[1]] = str(payload)[:200]
        _broadcast("task_update", {"task_id": task_id, "event": rest[1] if len(rest) >= 2 else "data"})

def mqtt_loop():
    global mqtt_client
    while True:
        try:
            # 先断开旧的 client，防止残留 loop 线程干扰
            if mqtt_client is not None:
                try:
                    mqtt_client.disconnect()
                except:
                    pass
                mqtt_client = None

            kwargs = {}
            if MQTT_USER:
                kwargs["username"] = MQTT_USER
                kwargs["password"] = MQTT_PASS
            c = BBSClient("dashboard", host=BROKER_HOST, port=BROKER_PORT, **kwargs)
            c._client.reconnect_delay_set(0)  # 禁用 paho 自动重连
            c.connect()
            if c.wait_connected(timeout=5):
                mqtt_client = c
                _log("info", "system", f"MQTT connected to {BROKER_HOST}:{BROKER_PORT}")
                c._client.subscribe("agent/#")

                def on_msg(cl, ud, msg):
                    try:
                        pl = json.loads(msg.payload)
                    except:
                        pl = msg.payload.decode(errors="replace")
                    _on_message(msg.topic, pl)
                c._client.on_message = on_msg

                # 不使用 paho 自动重连，断开后由外层循环重建
                while mqtt_client is c and c._connected:
                    time.sleep(1)
                _log("warn", "system", "MQTT disconnected, reconnecting...")
            else:
                _log("error", "system", "MQTT connection timeout, retry in 10s")
                time.sleep(10)
        except Exception as e:
            _log("error", "system", f"MQTT error: {e}")
            time.sleep(5)

@get("/")
def index():
    return HTML

@get("/api/agents")
def api_agents():
    response.content_type = "application/json"
    return json.dumps(agents)

@get("/api/tasks")
def api_tasks():
    response.content_type = "application/json"
    return json.dumps(tasks)

@get("/api/logs")
def api_logs():
    response.content_type = "application/json"
    return json.dumps(log_events[-50:])

@get("/api/publish")
def api_publish():
    topic = request.query.topic
    msg = request.query.msg
    if mqtt_client:
        mqtt_client.publish(topic, msg, qos=1)
        _log("info", "web", f"PUB {topic}: {msg[:100]}")
    return "ok"

@get("/api/events")
def sse():
    """SSE endpoint - requires a server that supports streaming"""
    response.content_type = "text/event-stream"
    return "data: {}\n\n"

mqtt_client = None

HTML = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><title>rmqtt Web UI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#1a1a2e;color:#e0e0e0;margin:0;padding:20px}
h1{color:#00d2ff;font-size:20px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.card{background:#16213e;border-radius:8px;padding:16px;border:1px solid #0f3460}
.card h2{font-size:14px;color:#00d2ff;margin-bottom:8px}
.agent-item{padding:4px 0;font-size:13px;border-bottom:1px solid #0f3460}
.agent-item .status{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.status-online{background:#00ff88}.status-offline{background:#ff4444}
.log-box{background:#0d1117;padding:10px;border-radius:4px;height:200px;overflow-y:auto;font-family:monospace;font-size:12px}
.log-line{padding:1px 0}.log-ERROR{color:#ff4444}.log-info{color:#888}
.pub-form{display:flex;gap:8px;margin-top:8px}
.pub-form input{flex:1;background:#0d1117;border:1px solid #0f3460;padding:6px;border-radius:4px;color:#fff}
.pub-form button{background:#00d2ff;color:#000;border:none;padding:6px 12px;border-radius:4px;cursor:pointer}
</style></head><body>
<h1>rmqtt Web UI</h1>
<div class="grid">
<div class="card"><h2>Agents (<span id="agent-count">0</span>)</h2><div id="agents"></div></div>
<div class="card"><h2>Tasks (<span id="task-count">0</span>)</h2><div id="tasks"></div></div>
</div>
<div class="card"><h2>Live Log</h2><div class="log-box" id="log"></div></div>
<div class="card"><h2>Publish</h2>
<form class="pub-form" onsubmit="pub(event)"><input id="pub-topic" placeholder="agent/board/task/hello/input" value="agent/board/task/test/input"><input id="pub-msg" placeholder='{"msg":"hello"}'><button type="submit">Publish</button></form></div>
<script>
function ra(i,a){var e=document.getElementById(i);e.innerHTML='';if(Object.keys(a).length===0){e.innerHTML='<div style="color:#666;font-size:13px">(none)</div>';return}
Object.entries(a).forEach(function([k,v]){var d=document.createElement('div');d.className='agent-item'
var s=document.createElement('span');s.className='status status-'+(v.status||'offline');d.appendChild(s)
d.append(k+' ('+(v.status||'?')+') '+ (v.last_seen||''));e.appendChild(d)})}
function rt(i,a){var e=document.getElementById(i);e.innerHTML='';if(Object.keys(a).length===0){e.innerHTML='<div style="color:#666;font-size:13px">(none)</div>';return}
Object.entries(a).forEach(function([k,v]){var d=document.createElement('div');d.className='agent-item';d.textContent=k+' - '+(v.status||v.updated_at||'');e.appendChild(d)})}
function pub(e){e.preventDefault();fetch('/api/publish?topic='+encodeURIComponent(document.getElementById('pub-topic').value)+'&msg='+encodeURIComponent(document.getElementById('pub-msg').value));document.getElementById('pub-msg').value=''}
var logCache='';
function fetchLogs(){fetch('/api/logs').then(function(r){return r.json()}).then(function(d){var e=document.getElementById('log');var h='';d.forEach(function(l){var c=l[1]==='error'?'log-ERROR':'log-info';h+='<div class="log-line '+c+'">['+l[0]+']['+l[1]+']['+l[2]+'] '+l[3]+'</div>'});if(h!==logCache){e.innerHTML=h;e.scrollTop=e.scrollHeight;logCache=h}})}
setInterval(function(){fetchAgents();fetchTasks();fetchLogs()},2000)
function fetchAgents(){fetch('/api/agents').then(function(r){return r.json()}).then(function(d){ra('agents',d);document.getElementById('agent-count').textContent=Object.keys(d).length})}
function fetchTasks(){fetch('/api/tasks').then(function(r){return r.json()}).then(function(d){rt('tasks',d);document.getElementById('task-count').textContent=Object.keys(d).length})}
fetchAgents();fetchTasks();fetchLogs();
</script></body></html>
"""


if __name__ == "__main__":
    print(f"[rmqtt] Web UI http://127.0.0.1:{WEB_PORT}")
    t = threading.Thread(target=mqtt_loop, daemon=True)
    t.start()
    time.sleep(0.5)
    run(host="127.0.0.1", port=WEB_PORT, server="auto", quiet=True)
