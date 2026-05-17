"""Second patch - use exact strings from the file"""
with open(r'D:\open_claw_agent\GenericAgent_mqtt\tools\rmqtt_webui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add stats history endpoint before broker_loop
old1 = '''    except Exception:
        pass  # DB not available, will retry later


def broker_loop():'''

new1 = '''    except Exception:
        pass  # DB not available, will retry later


@get("/api/stats/history")
def api_stats_history():
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

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("✅ API endpoint added")
else:
    print("❌ old1 not found")

# Add Stats History card to HTML (after Tasks card)
old_grid = '''<div class="card"><h2>Tasks (<span id="task-count">0</span>)</h2><div id="tasks"></div></div>
</div>
<div class="card"><h2>Live Log</h2>'''

new_grid = '''<div class="card"><h2>Tasks (<span id="task-count">0</span>)</h2><div id="tasks"></div></div>
</div>
<div class="card"><h2>Stats (last 1h)</h2><div id="stats-history" style="font-size:12px;color:#94a3b8;line-height:1.6;max-height:120px;overflow-y:auto">(collecting...)</div></div>
<div class="card"><h2>Live Log</h2>'''

if old_grid in content:
    content = content.replace(old_grid, new_grid, 1)
    print("✅ Stats card added to HTML")
else:
    print("❌ old_grid not found")

# Add fetchStats to the setInterval
old_interval = '''setInterval(function(){fetchAgents();fetchTasks();fetchLogs();fetchBroker()},3000)'''
new_interval = '''setInterval(function(){fetchAgents();fetchTasks();fetchLogs();fetchBroker();fetchStats()},5000)'''

if old_interval in content:
    content = content.replace(old_interval, new_interval, 1)
    print("✅ fetchStats added to interval")
else:
    print("❌ old_interval not found")

# Add fetchStats function before fetchAgents
old_fa = '''function fetchAgents(){fetch('/api/agents')'''
new_fa = '''function fetchStats(){fetch('/api/stats/history').then(function(r){return r.json()}).then(function(d){
var e=document.getElementById('stats-history');if(!e)return;if(d.length===0){e.innerHTML='<span style="color:#666">(no data)</span>';return}
var h='';var step=Math.max(1,Math.floor(d.length/15));for(var i=d.length-1;i>=0;i-=step){
var r=d[i];h+=r.ts.substr(5,11)+' C:'+r.c+' T:'+r.t+' S:'+r.s+' R:'+r.r+'<br>'}
e.innerHTML=h})}
function fetchAgents(){fetch('/api/agents')'''

if old_fa in content:
    content = content.replace(old_fa, new_fa, 1)
    print("✅ fetchStats function added")
else:
    print("❌ old_fa not found")

with open(r'D:\open_claw_agent\GenericAgent_mqtt\tools\rmqtt_webui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ File saved")
