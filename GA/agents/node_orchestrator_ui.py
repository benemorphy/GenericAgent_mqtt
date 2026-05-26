"""
Node Orchestrator UI — FastAPI 服务 (v2 修复版)
三层组合架构中的 "Node UI (可视化编排层)"
=============================================
v2 修复:
  1. 节点连线: 端口使用大点击区域(20px)+坐标邻近检测
  2. 执行错误: LangGraph在ThreadPool中运行,避免async冲突
  3. Agent配置: 双击节点弹出配置面板(任务/模型/参数)
"""

import os, sys, json, importlib, asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

app = FastAPI(title="Multi-Agent Orchestrator", version="2.0.0")
_executor = ThreadPoolExecutor(max_workers=2)

HTML_PAGE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Multi-Agent Orchestrator v2</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;height:100vh;display:flex;flex-direction:column;overflow:hidden;}
header{background:#16213e;padding:10px 20px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #0f3460;flex-shrink:0;}
header h1{font-size:16px;color:#e94560;flex:1;}
header button{background:#e94560;color:#fff;border:none;padding:6px 16px;border-radius:4px;cursor:pointer;font-size:13px;}
header button:hover{background:#c73652;}
header #status{font-size:12px;color:#aaa;}

#main{display:flex;flex:1;overflow:hidden;}
#canvas-wrap{flex:1;position:relative;background:#16213e;}
#svg-canvas{width:100%;height:100%;display:block;}

/* 节点样式 */
.node rect.bg{fill:#0f3460;stroke:#533483;stroke-width:2;rx:6;}
.node:hover rect.bg{stroke:#e94560;}
.node text.title{fill:#e94560;font-size:13px;font-weight:bold;text-anchor:middle;}
.node .port{ cursor:crosshair; }
.node .port .hit{fill:transparent;stroke:none;cursor:crosshair;}
.node .port:hover .hit{fill:rgba(233,69,96,0.15);}
.node .port .dot{fill:#533483;stroke:#e94560;stroke-width:2;r:5;pointer-events:none;}
.node .port:hover .dot{fill:#e94560;}
.node .port-label{fill:#aaa;font-size:10px;pointer-events:none;}
.node .port-in .port-label{fill:#4fc3f7;}
.node .port-out .port-label{fill:#ffb74d;}

.edge{stroke:#533483;stroke-width:2;fill:none;marker-end:url(#arrow);cursor:pointer;}
.edge:hover{stroke:#e94560;stroke-width:3;}
.temp-line{stroke:#e94560;stroke-width:2;stroke-dasharray:5,5;fill:none;pointer-events:none;}

/* 右侧配置面板 */
#config-panel{width:280px;background:#0f3460;border-left:1px solid #1a1a2e;padding:16px;display:flex;flex-direction:column;gap:10px;overflow-y:auto;flex-shrink:0;}
#config-panel h3{font-size:14px;color:#e94560;border-bottom:1px solid #533483;padding-bottom:6px;}
#config-panel label{font-size:12px;color:#aaa;}
#config-panel input,#config-panel select,#config-panel textarea{width:100%;background:#16213e;border:1px solid #533483;color:#eee;padding:6px 8px;border-radius:4px;font-size:12px;margin-top:2px;}
#config-panel textarea{resize:vertical;min-height:50px;font-family:inherit;}
#config-panel .field{margin-bottom:8px;}
#config-panel .node-list-item{padding:6px 8px;margin:2px 0;background:#16213e;border-radius:4px;cursor:pointer;font-size:12px;border:1px solid transparent;}
#config-panel .node-list-item:hover{border-color:#533483;}
#config-panel .node-list-item.active{border-color:#e94560;background:#1a2744;}

#result-panel{display:none;position:fixed;bottom:0;left:0;right:0;height:180px;background:#0a0a1a;border-top:2px solid #533483;overflow:auto;padding:12px;font-size:12px;z-index:100;}
#result-panel pre{margin:0;white-space:pre-wrap;font-family:'Consolas',monospace;font-size:11px;color:#ccc;}
</style>
</head>
<body>

<header>
  <h1>Multi-Agent Orchestrator v2</h1>
  <span id="status">ready</span>
  <button onclick="executeGraph()">Execute</button>
  <button onclick="exportConfig()">Export</button>
  <button onclick="clearAll()">Clear</button>
</header>

<div id="main">
  <div id="canvas-wrap">
    <svg id="svg-canvas" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#533483" />
        </marker>
      </defs>
    </svg>
  </div>
  <div id="config-panel">
    <h3>Node Config</h3>
    <div id="node-list"></div>
    <div id="node-config" style="display:none;">
      <div id="cfg-fields-agent" style="display:none;">
        <div class="field">
          <label>Task / Prompt</label>
          <textarea id="cfg-task" rows="2" placeholder="Task description for this agent...">Multi-agent reflection norms research</textarea>
        </div>
        <div class="field">
          <label>Model</label>
          <select id="cfg-model">
            <option value="gpt-4">GPT-4</option>
            <option value="gpt-3.5">GPT-3.5</option>
            <option value="claude-3">Claude-3</option>
            <option value="local" selected>Local (default)</option>
          </select>
        </div>
        <div class="field">
          <label>Max Iterations</label>
          <input id="cfg-iter" type="number" value="2" min="1" max="10">
        </div>
        <div class="field">
          <label>Temperature</label>
          <input id="cfg-temp" type="range" min="0" max="20" value="7">
          <span id="cfg-temp-val" style="font-size:12px;color:#aaa;">0.7</span>
        </div>
      </div>
      <div id="cfg-fields-data" style="display:none;">
        <div class="field">
          <label>Input Data</label>
          <textarea id="cfg-data" rows="6" placeholder="Enter data content for the DataSource node...
This can be text, JSON, CSV, or any data format.
Connected agents will receive this as input.">Sample research data:
- Paper A: Multi-agent reflection mechanisms
- Paper B: Social norms in agent societies
- Paper C: LangGraph orchestration patterns</textarea>
        </div>
      </div>
    </div>
    <div style="margin-top:auto;padding-top:8px;border-top:1px solid #533483;">
      <p style="font-size:11px;color:#666;">Drag nodes from toolbox,<br>drag between ports to connect,<br>click node to configure.</p>
    </div>
  </div>
</div>

<div id="result-panel"><pre id="result-content">Waiting...</pre></div>

<script>
const NODE_W = 170, NODE_H = 54, PORT_H = 22, HIT_W = 22;
const svg = document.getElementById('svg-canvas');
const wrap = document.getElementById('canvas-wrap');

const NODE_META = {
  search:  {label:'SearchAgent', color:'#4fc3f7', inputs:[], outputs:['search_results']},
  analyze: {label:'AnalyzeAgent', color:'#ffb74d', inputs:['search_results','data'], outputs:['analysis']},
  summary: {label:'SummaryAgent', color:'#81c784', inputs:['analysis'], outputs:['summary']},
  reflect: {label:'ReflectionAgent', color:'#ce93d8', inputs:['summary'], outputs:['action']},
  data:    {label:'DataSource',   color:'#90caf9', inputs:[], outputs:['data']}
};

let nodes={}, edges=[], nid=0, selectedNode=null, dragState=null, connState=null;
let mouseX=0, mouseY=0;

/* ===== SVG坐标工具 ===== */
function svgPoint(clientX, clientY) {
  const pt = svg.createSVGPoint(); pt.x=clientX; pt.y=clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

/* ===== 添加节点 ===== */
function addNode(type, x, y) {
  const id='n'+(nid++), meta=NODE_META[type];
  if(!meta) return;
  const numPorts=Math.max(meta.inputs.length,meta.outputs.length);
  const h=NODE_H+numPorts*PORT_H;
  const g=document.createElementNS('http://www.w3.org/2000/svg','g');
  g.setAttribute('class','node'); g.id=id;

  const bg=document.createElementNS('http://www.w3.org/2000/svg','rect');
  bg.setAttribute('class','bg'); bg.setAttribute('width',NODE_W); bg.setAttribute('height',h);
  g.appendChild(bg);

  const t=document.createElementNS('http://www.w3.org/2000/svg','text');
  t.setAttribute('class','title'); t.setAttribute('x',NODE_W/2); t.setAttribute('y',22);
  t.textContent=meta.label; g.appendChild(t);

  // 输入端口 (左侧)
  meta.inputs.forEach((pName,i)=>{
    const py=36+i*PORT_H;
    const pg=document.createElementNS('http://www.w3.org/2000/svg','g');
    pg.setAttribute('class','port port-in');
    pg.dataset.nodeId=id; pg.dataset.dir='in'; pg.dataset.port=pName;

    const hit=document.createElementNS('http://www.w3.org/2000/svg','rect');
    hit.setAttribute('class','hit');
    hit.setAttribute('x',-HIT_W/2); hit.setAttribute('y',py-HIT_W/2);
    hit.setAttribute('width',HIT_W); hit.setAttribute('height',HIT_W);
    hit.setAttribute('rx',4);
    pg.appendChild(hit);

    const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
    dot.setAttribute('class','dot');
    dot.setAttribute('cx',0); dot.setAttribute('cy',py);
    pg.appendChild(dot);

    const lb=document.createElementNS('http://www.w3.org/2000/svg','text');
    lb.setAttribute('class','port-label');
    lb.setAttribute('x',10); lb.setAttribute('y',py+4);
    lb.textContent=pName; pg.appendChild(lb);

    pg.addEventListener('mousedown',e=>{e.stopPropagation(); startConn(id,'in',pName,e);});
    g.appendChild(pg);
  });

  // 输出端口 (右侧)
  meta.outputs.forEach((pName,i)=>{
    const py=36+i*PORT_H;
    const pg=document.createElementNS('http://www.w3.org/2000/svg','g');
    pg.setAttribute('class','port port-out');
    pg.dataset.nodeId=id; pg.dataset.dir='out'; pg.dataset.port=pName;

    const hit=document.createElementNS('http://www.w3.org/2000/svg','rect');
    hit.setAttribute('class','hit');
    hit.setAttribute('x',NODE_W-HIT_W/2); hit.setAttribute('y',py-HIT_W/2);
    hit.setAttribute('width',HIT_W); hit.setAttribute('height',HIT_W);
    hit.setAttribute('rx',4);
    pg.appendChild(hit);

    const dot=document.createElementNS('http://www.w3.org/2000/svg','circle');
    dot.setAttribute('class','dot');
    dot.setAttribute('cx',NODE_W); dot.setAttribute('cy',py);
    pg.appendChild(dot);

    const lb=document.createElementNS('http://www.w3.org/2000/svg','text');
    lb.setAttribute('class','port-label');
    lb.setAttribute('x',NODE_W-10); lb.setAttribute('y',py+4);
    lb.setAttribute('text-anchor','end');
    lb.textContent=pName; pg.appendChild(lb);

    pg.addEventListener('mousedown',e=>{e.stopPropagation(); startConn(id,'out',pName,e);});
    g.appendChild(pg);
  });

  g.setAttribute('transform',`translate(${x},${y})`);
  g.addEventListener('mousedown',e=>{
    if(e.button!==0) return;
    const pt=svgPoint(e.clientX,e.clientY);
    dragState={g,ox:e.clientX-pt.x,oy:e.clientY-pt.y,startX:x,startY:y};
    selectNode(id);
  });
  g.addEventListener('dblclick',()=>{ selectNode(id); });
  svg.appendChild(g);
  nodes[id]={id,type,x,y,g,config:{task:'',model:'local',iterations:2,temperature:0.7}};
  updateNodeList();
  return id;
}

/* ===== 连线逻辑 ===== */
function startConn(nodeId,dir,port,e){
  e.stopPropagation();
  const pt=svgPoint(e.clientX,e.clientY);
  connState={nodeId,dir,port,startX:pt.x,startY:pt.y};
  const line=document.createElementNS('http://www.w3.org/2000/svg','line');
  line.setAttribute('class','temp-line');
  line.setAttribute('x1',pt.x); line.setAttribute('y1',pt.y);
  line.setAttribute('x2',pt.x); line.setAttribute('y2',pt.y);
  svg.appendChild(line);
}

function finishConn(e){
  if(!connState) return;
  const pt=svgPoint(e.clientX,e.clientY);
  // 找最近的端口(40px内)
  let best=null, bestDist=40;
  document.querySelectorAll('.port').forEach(pg=>{
    const dir=pg.dataset.dir;
    if(dir===connState.dir) return; // 同方向不行
    const nid=pg.dataset.nodeId;
    if(nid===connState.nodeId) return; // 同节点不行
    const box=pg.getBoundingClientRect();
    const cx=box.left+box.width/2, cy=box.top+box.height/2;
    const d=Math.hypot(e.clientX-cx, e.clientY-cy);
    if(d<bestDist){bestDist=d; best=pg;}
  });
  if(best){
    const fromNode=connState.dir==='out'?connState.nodeId:best.dataset.nodeId;
    const fromPort=connState.dir==='out'?connState.port:best.dataset.port;
    const toNode=connState.dir==='out'?best.dataset.nodeId:connState.nodeId;
    const toPort=connState.dir==='out'?best.dataset.port:connState.port;
    addEdge(fromNode,fromPort,toNode,toPort);
  }
  connState=null;
  document.querySelector('.temp-line')?.remove();
}

/* ===== 添加边 ===== */
function addEdge(from,fromPort,to,toPort){
  // 去重
  if(edges.some(e=>e.from===from&&e.to===to)) return;
  edges.push({from,fromPort,to,toPort});
  drawEdges();
}

function drawEdges(){
  document.querySelectorAll('.edge').forEach(el=>el.remove());
  edges.forEach((e,i)=>{
    const line=document.createElementNS('http://www.w3.org/2000/svg','line');
    line.setAttribute('class','edge'); line.id='e'+i;
    svg.appendChild(line);
  });
  updateEdgePos();
}

function updateEdgePos(){
  edges.forEach((e,i)=>{
    const line=document.getElementById('e'+i);
    if(!line) return;
    const fg=document.getElementById(e.from), tg=document.getElementById(e.to);
    if(!fg||!tg) return;
    const fm=fg.getAttribute('transform').match(/translate\(([^,]+),([^)]+)\)/);
    const tm=tg.getAttribute('transform').match(/translate\(([^,]+),([^)]+)\)/);
    if(!fm||!tm) return;
    line.setAttribute('x1',parseFloat(fm[1])+NODE_W);
    line.setAttribute('y1',parseFloat(fm[2])+36);
    line.setAttribute('x2',parseFloat(tm[1]));
    line.setAttribute('y2',parseFloat(tm[2])+36);
  });
}

/* ===== 鼠标事件 ===== */
document.addEventListener('mousemove',e=>{
  mouseX=e.clientX; mouseY=e.clientY;
  if(dragState){
    const pt=svgPoint(e.clientX,e.clientY);
    const x=pt.x-dragState.ox, y=pt.y-dragState.oy;
    dragState.g.setAttribute('transform',`translate(${x},${y})`);
    if(nodes[dragState.g.id]){nodes[dragState.g.id].x=x; nodes[dragState.g.id].y=y;}
    updateEdgePos();
  }
  if(connState){
    const pt=svgPoint(e.clientX,e.clientY);
    document.querySelector('.temp-line')?.setAttribute('x2',pt.x);
    document.querySelector('.temp-line')?.setAttribute('y2',pt.y);
  }
});
document.addEventListener('mouseup',e=>{
  dragState=null;
  finishConn(e);
});

/* ===== 选中/配置 ===== */
function selectNode(id){
  selectedNode=id;
  document.querySelectorAll('.node-list-item').forEach(el=>el.classList.toggle('active',el.dataset.id===id));
  const n=nodes[id];
  if(!n){document.getElementById('node-config').style.display='none'; return;}
  const cfg=n.config||{};
  document.getElementById('node-config').style.display='block';

  // 根据节点类型显示不同配置
  const isData = n.type === 'data';
  document.getElementById('cfg-fields-agent').style.display = isData ? 'none' : 'block';
  document.getElementById('cfg-fields-data').style.display = isData ? 'block' : 'none';

  document.getElementById('cfg-task').value=cfg.task||'';
  document.getElementById('cfg-model').value=cfg.model||'local';
  document.getElementById('cfg-iter').value=cfg.iterations||2;
  document.getElementById('cfg-temp').value=(cfg.temperature||0.7)*10;
  document.getElementById('cfg-temp-val').textContent=(cfg.temperature||0.7).toFixed(1);
  document.getElementById('cfg-data').value=cfg.data||'';
}

// 配置变化时保存
document.getElementById('cfg-task').addEventListener('input',saveCfg);
document.getElementById('cfg-model').addEventListener('change',saveCfg);
document.getElementById('cfg-iter').addEventListener('change',saveCfg);
document.getElementById('cfg-temp').addEventListener('input',function(){
  document.getElementById('cfg-temp-val').textContent=(this.value/10).toFixed(1);
  saveCfg();
});
function saveCfg(){
  if(!selectedNode||!nodes[selectedNode]) return;
  const isData = nodes[selectedNode].type === 'data';
  nodes[selectedNode].config={
    task:document.getElementById('cfg-task').value,
    model:document.getElementById('cfg-model').value,
    iterations:parseInt(document.getElementById('cfg-iter').value)||2,
    temperature:parseInt(document.getElementById('cfg-temp').value)/10,
    data:document.getElementById('cfg-data').value
  };
  document.getElementById('status').textContent='config saved';
  setTimeout(()=>document.getElementById('status').textContent='ready',1000);
}

function updateNodeList(){
  const list=document.getElementById('node-list');
  list.innerHTML='';
  Object.values(nodes).forEach(n=>{
    const div=document.createElement('div');
    div.className='node-list-item';
    div.dataset.id=n.id;
    div.textContent=`${NODE_META[n.type]?.label||n.type} (${n.id})`;
    div.onclick=()=>selectNode(n.id);
    list.appendChild(div);
  });
}

/* ===== 构建JSON ===== */
function buildGraphJSON(){
  return{
    nodes:Object.values(nodes).map(n=>({id:n.id,type:n.type,x:n.x,y:n.y,config:n.config||{}})),
    edges:edges.map(e=>({from:e.from,fromPort:e.fromPort,to:e.to,toPort:e.toPort}))
  };
}

/* ===== 执行 ===== */
async function executeGraph(){
  const graph=buildGraphJSON();
  if(graph.nodes.length===0){alert('Add nodes first');return;}
  document.getElementById('status').textContent='running...';
  document.getElementById('result-panel').style.display='block';
  document.getElementById('result-content').textContent='Executing pipeline...\n';

  const globalTask=document.getElementById('cfg-task').value||'Multi-agent system research';
  const globalModel=document.getElementById('cfg-model').value||'local';
  const globalIter=parseInt(document.getElementById('cfg-iter').value)||2;
  const globalTemp=parseInt(document.getElementById('cfg-temp').value)/10;

  try{
    const resp=await fetch('/api/execute',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({graph,global_task:globalTask,global_model:globalModel,global_iterations:globalIter,global_temperature:globalTemp})
    });
    const data=await resp.json();
    document.getElementById('result-content').textContent=JSON.stringify(data,null,2);
    document.getElementById('status').textContent=data.status==='success'?'done':'error';
  }catch(e){
    document.getElementById('result-content').textContent='Error: '+e.message;
    document.getElementById('status').textContent='error';
  }
}

/* ===== 导出/清空 ===== */
function exportConfig(){
  const json=JSON.stringify(buildGraphJSON(),null,2);
  navigator.clipboard.writeText(json);
  document.getElementById('status').textContent='copied!';
  setTimeout(()=>document.getElementById('status').textContent='ready',1500);
}
function clearAll(){
  Object.values(nodes).forEach(n=>n.g.remove());
  nodes={};edges=[];nid=0;selectedNode=null;
  document.querySelectorAll('.edge,.temp-line').forEach(e=>e.remove());
  document.getElementById('node-config').style.display='none';
  updateNodeList();
  document.getElementById('status').textContent='cleared';
}

/* ===== 拖放添加 ===== */
['search','analyze','summary','reflect','data'].forEach(type=>{
  const btn=document.createElement('div');
  btn.style.cssText='position:fixed;right:302px;'+(type==='search'?'top:64px;':'top:'+(64+36*['search','analyze','summary','reflect'].indexOf(type))+'px;')+
    'background:#0f3460;color:#eee;padding:6px 12px;border-radius:4px;cursor:grab;font-size:12px;z-index:50;border:1px solid #533483;';
  btn.textContent='+ '+NODE_META[type].label;
  btn.draggable=true;
  btn.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',type));
  document.body.appendChild(btn);
});
wrap.addEventListener('dragover',e=>e.preventDefault());
wrap.addEventListener('drop',e=>{
  e.preventDefault();
  const type=e.dataTransfer.getData('text/plain');
  if(!NODE_META[type])return;
  const rect=svg.getBoundingClientRect();
  const pt=svgPoint(e.clientX,e.clientY);
  addNode(type,pt.x-rect.left-NODE_W/2,pt.y-rect.top-30);
});

/* ===== 初始化示例 ===== */
addNode('data',-10,100);      // DataSource 提供输入数据
addNode('search',170,20);
addNode('analyze',410,20);
addNode('summary',650,20);
addNode('reflect',650,180);
// 连线: data -> analyze, search -> analyze, analyze -> summary -> reflect
edges.push({ from:'n0', fromPort:'data', to:'n2', toPort:'data' });
edges.push({ from:'n1', fromPort:'search_results', to:'n2', toPort:'search_results' });
edges.push({ from:'n2', fromPort:'analysis', to:'n3', toPort:'analysis' });
edges.push({ from:'n3', fromPort:'summary', to:'n4', toPort:'summary' });
drawEdges();
document.querySelector('#node-list .node-list-item')?.click();
</script>
</body>
</html>
'''

# ===== FastAPI 路由 =====

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

@app.get("/api/nodes")
async def get_node_definitions():
    try:
        mod = importlib.import_module("langgraph_multi_agent")
        return {"nodes": getattr(mod, "NODE_DEFINITIONS", [])}
    except Exception as e:
        return {"nodes": [], "error": str(e)}

def _run_pipeline(task: str, max_iter: int, graph_data: dict = None):
    """在独立线程中运行LangGraph"""
    mod = importlib.import_module("langgraph_multi_agent")
    run_func = getattr(mod, "run_pipeline", None)
    if run_func:
        # 提取data节点内容
        data_content = ""
        if graph_data:
            for node in graph_data.get("nodes", []):
                if node.get("type") == "data":
                    data_content = node.get("config", {}).get("data", "") or ""
        return run_func(task, max_iterations=max_iter, data_input=data_content)
    raise RuntimeError("langgraph_multi_agent 模块缺少 run_pipeline 函数")

@app.post("/api/execute")
async def execute_graph(data: dict):
    """执行节点图 (在ThreadPool中运行LangGraph避免async冲突)"""
    try:
        graph = data.get("graph", {})
        global_task = data.get("global_task", "Multi-agent system research")
        global_iterations = data.get("global_iterations", 2)

        # 在独立线程中运行，避免 Windows asyncio 冲突
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor, _run_pipeline, global_task, global_iterations, graph
        )

        return {
            "status": "success",
            "summary": result.get("summary", "")[:1000],
            "iteration": result.get("iteration", 0),
            "logs": result.get("logs", []),
            "graph_nodes": len(graph.get("nodes", [])),
            "graph_edges": len(graph.get("edges", []))
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== 启动入口 =====

def start_server(port: int = 8765, host: str = "127.0.0.1"):
    """启动 Node UI 服务"""
    print(f"[NodeUI] Multi-Agent Orchestrator v2")
    print(f"   启动: http://{host}:{port}")
    print(f"   拖拽节点编排 -> 点击执行 -> 查看结果")
    uvicorn.run(app, host=host, port=port, log_level="error")

if __name__ == "__main__":
    start_server()