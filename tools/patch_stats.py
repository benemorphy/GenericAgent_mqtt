"""Apply broker stats time-series recording to rmqtt_webui.py"""
import sys
sys.path.insert(0, r'D:\open_claw_agent\GenericAgent_mqtt')

with open(r'D:\open_claw_agent\GenericAgent_mqtt\tools\rmqtt_webui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Stats recording in broker_loop (every 4th tick ~12s)
old_tick = '''            tick += 1
            if tick % 2 == 0:
                fetch_db_tasks()'''

new_tick = '''            tick += 1
            if tick % 2 == 0:
                fetch_db_tasks()
            if tick % 4 == 0 and broker_cache.get("stats"):
                try:
                    import pymysql as _pm
                    s = broker_cache["stats"]
                    c = _pm.connect(host="127.0.0.1",port=3306,user="root",password="mariadb",database="mqtt_bbs",connect_timeout=2)
                    with c.cursor() as cur:
                        cur.execute(
                            "INSERT INTO broker_stats(connections,topics,subscriptions,routes,uptime_secs) VALUES(%s,%s,%s,%s,%s)",
                            (s.get("connections.count",0), s.get("topics.count",0),
                             s.get("subscriptions.count",0), s.get("routes.count",0),
                             broker_cache["info"].get("uptime",0) if broker_cache.get("info") else 0))
                    c.close()
                except Exception:
                    pass'''

if old_tick in content:
    content = content.replace(old_tick, new_tick, 1)
    print("✅ Stats recording added to broker_loop")
else:
    print("❌ old_tick not found")

# 2. Add API endpoints for stats history
old_after = '''@get("/api/subs")
def api_broker_subs():
    response.content_type = "application/json"
    return json.dumps(broker_cache.get("subs", []))


def broker_loop():'''

new_after = '''@get("/api/subs")
def api_broker_subs():
    response.content_type = "application/json"
    return json.dumps(broker_cache.get("subs", []))

@get("/api/stats/history")
def api_stats_history():
    """返回最近1小时 broker 统计时序数据"""
    try:
        import pymysql as _pm
        c = _pm.connect(host="127.0.0.1",port=3306,user="root",password="mariadb",database="mqtt_bbs",connect_timeout=2)
        with c.cursor() as cur:
            cur.execute("SELECT ts,connections,topics,subscriptions,routes FROM broker_stats WHERE ts > NOW() - INTERVAL 1 HOUR ORDER BY ts")
            rows = [{"ts":str(r[0]),"c":r[1],"t":r[2],"s":r[3],"r":r[4]} for r in cur.fetchall()]
        c.close()
        response.content_type = "application/json"
        return json.dumps(rows)
    except Exception:
        response.content_type = "application/json"
        return json.dumps([])

def broker_loop():'''

if old_after in content:
    content = content.replace(old_after, new_after, 1)
    print("✅ Stats history endpoint added")
else:
    print("❌ old_after not found")

# 3. Add Stats card to HTML and fetch JS
old_grid_end = '''<div class="card"><h2>Tasks (<span id="task-count">0</span>)</h2><div id="tasks"><div style="color:#666">(none)</div></div></div>
</div>
<div class="card"><h2>Live Log</h2>
<div class="log-box" id="log"></div></div>'''

new_grid_end = '''<div class="card"><h2>Tasks (<span id="task-count">0</span>)</h2><div id="tasks"><div style="color:#666">(none)</div></div></div>
</div>
<div class="card"><h2>Stats History (last 1h)</h2><div id="stats-history" style="font-size:12px;color:#94a3b8;line-height:1.6;max-height:120px;overflow-y:auto"></div></div>
<div class="card"><h2>Live Log</h2>
<div class="log-box" id="log"></div></div>'''

if old_grid_end in content:
    content = content.replace(old_grid_end, new_grid_end, 1)
    print("✅ Stats card added to HTML")
else:
    print("❌ old_grid_end not found")

# 4. Add fetchStats to JS
old_fetch = '''function fetchBroker(){fetch('/api/broker').then(function(r){return r.json()}).then(function(d){
var bi=document.getElementById('broker-info');var bn=document.getElementById('broker-node');
bn.textContent=d.info.node_id+'@'+d.info.node_name||'';
bi.innerHTML='Version: '+d.info.version+' | Uptime: '+d.info.uptime+'s<br>Connections: '+d.stats["connections.count"]+' | Topics: '+d.stats["topics.count"]+'Subscriptions: '+d.stats["subscriptions.count"]+' | Routes: '+d.stats["routes.count"]}})
setInterval(function(){fetchAgents();fetchTasks();fetchLogs();fetchBroker()},3000)'''

new_fetch = '''function fetchBroker(){fetch('/api/broker').then(function(r){return r.json()}).then(function(d){
var bi=document.getElementById('broker-info');var bn=document.getElementById('broker-node');
bn.textContent=d.info.node_id+'@'+d.info.node_name||'';
bi.innerHTML='Version: '+d.info.version+' | Uptime: '+d.info.uptime+'s<br>Connections: '+d.stats["connections.count"]+' | Topics: '+d.stats["topics.count"]+'Subscriptions: '+d.stats["subscriptions.count"]+' | Routes: '+d.stats["routes.count"]}})
function fetchStats(){fetch('/api/stats/history').then(function(r){return r.json()}).then(function(d){
var e=document.getElementById('stats-history');if(d.length===0){e.innerHTML='<span style="color:#666">(no data yet)</span>';return}
var h='';var step=Math.max(1,Math.floor(d.length/20));for(var i=d.length-1;i>=0;i-=step){
var r=d[i];h+=r.ts.substr(11,5)+' C:'+r.c+' T:'+r.t+' S:'+r.s+' R:'+r.r+'<br>'}
e.innerHTML=h}})
setInterval(function(){fetchAgents();fetchTasks();fetchLogs();fetchBroker();fetchStats()},5000)'''

if old_fetch in content:
    content = content.replace(old_fetch, new_fetch, 1)
    print("✅ fetchStats JS added")
else:
    print("❌ old_fetch not found")

with open(r'D:\open_claw_agent\GenericAgent_mqtt\tools\rmqtt_webui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ File saved")
