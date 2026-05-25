"""Replace Chart.js with ECharts in rmqtt_webui.py"""
with open('tools/rmqtt_webui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace CDN
content = content.replace(
    'src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"',
    'src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js"'
)

# 2. Replace chart rendering in fetchStats
old_chart = '''if(window.statsChart)window.statsChart.destroy();
var ctx=e.getContext('2d');
window.statsChart=new Chart(ctx,{type:'line',
data:{labels:d.map(function(x){return x.ts.substring(11,16)}),
datasets:[
{label:'C',data:d.map(function(x){return x.c}),borderColor:'#00d2ff',backgroundColor:'rgba(0,210,255,0.1)',fill:true,tension:0.3,pointRadius:2},
{label:'T',data:d.map(function(x){return x.t}),borderColor:'#ffd700',backgroundColor:'rgba(255,215,0,0.1)',fill:true,tension:0.3,pointRadius:2},
{label:'S',data:d.map(function(x){return x.s}),borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,0.1)',fill:true,tension:0.3,pointRadius:2},
{label:'R',data:d.map(function(x){return x.r}),borderColor:'#ff6b6b',backgroundColor:'rgba(255,107,107,0.1)',fill:true,tension:0.3,pointRadius:2}
]},
options:{responsive:true,maintainAspectRatio:false,
plugins:{legend:{labels:{color:'#94a3b8',boxWidth:12,font:{size:10}}}},
scales:{x:{ticks:{color:'#666',font:{size:9},maxTicksLimit:10},grid:{color:'#1a1a2e'}},
y:{beginAtZero:true,ticks:{color:'#666',font:{size:9}},grid:{color:'#1a1a2e'}}}}
}})'''

new_chart = '''if(window.statsChart)window.statsChart.dispose();
var chart=echarts.init(e);
window.statsChart=chart;
chart.setOption({
tooltip:{trigger:'axis',textStyle:{fontSize:10}},
legend:{data:['C','T','S','R'],textStyle:{color:'#94a3b8',fontSize:10}},
grid:{left:35,right:10,top:20,bottom:20},
xAxis:{type:'category',data:d.map(function(x){return x.ts.substring(11,16)}),
axisLabel:{color:'#666',fontSize:9},axisLine:{lineStyle:{color:'#1a1a2e'}}},
yAxis:{type:'value',min:0,splitLine:{lineStyle:{color:'#1a1a2e'}},
axisLabel:{color:'#666',fontSize:9}},
series:[
{name:'C',type:'line',data:d.map(function(x){return x.c}),smooth:true,
lineStyle:{color:'#00d2ff',width:1.5},itemStyle:{color:'#00d2ff'},areaStyle:{color:'rgba(0,210,255,0.05)'}},
{name:'T',type:'line',data:d.map(function(x){return x.t}),smooth:true,
lineStyle:{color:'#ffd700',width:1.5},itemStyle:{color:'#ffd700'},areaStyle:{color:'rgba(255,215,0,0.05)'}},
{name:'S',type:'line',data:d.map(function(x){return x.s}),smooth:true,
lineStyle:{color:'#22c55e',width:1.5},itemStyle:{color:'#22c55e'},areaStyle:{color:'rgba(34,197,94,0.05)'}},
{name:'R',type:'line',data:d.map(function(x){return x.r}),smooth:true,
lineStyle:{color:'#ff6b6b',width:1.5},itemStyle:{color:'#ff6b6b'},areaStyle:{color:'rgba(255,107,107,0.05)'}}
]})'''

if old_chart in content:
    content = content.replace(old_chart, new_chart)
    print("✅ Chart replaced with ECharts")
else:
    print("❌ old_chart not found")
    # Debug
    idx = content.find('window.statsChart')
    if idx >= 0:
        print(f"Found at pos {idx}: {repr(content[idx:idx+200])}")

with open('tools/rmqtt_webui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ File saved")
