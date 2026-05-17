"""Replace Chart.js with ECharts in fetchStats - exact code match"""
with open('tools/rmqtt_webui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Exact old chart code (the Chart.js update+create pattern)
old = '''}if(window.statsChart){window.statsChart.data.labels=d.map(function(x){return x.ts.slice(11,16)})};
window.statsChart.data.datasets[0].data=d.map(function(x){return x.c});
window.statsChart.data.datasets[1].data=d.map(function(x){return x.t});
windo
...[Truncated]...
olor:'#ff6b6b',backgroundColor:'rgba(255,107,107,0.1)',fill:true,tension:0.3,pointRadius:2}
]},
options:{responsive:true,maintainAspectRatio:false,
plugins:{legend:{labels:{color:'#94a3b8',boxWidth:12,font:{size:10}}}},
scales:{x:{ticks:{color:'#666',font:{size:9},maxTicksLimit:10},grid:{color:'#1a1a2e'}},
y:{beginAtZero:true,ticks:{color:'#666',font:{size:9}},grid:{color:'#1a1a2e'}}}}
}})
'''

if old in content:
    content = content.replace(old, new)
    print("✅ Chart.js replaced with ECharts")
    print(f"   Old: {len(old)} chars, New: {len(new)} chars")
else:
    print("❌ Exact old code not found")
    # Partial check
    for keyword in ['window.statsChart.data.labels', 'new Chart(ctx']:
        print(f"   '{keyword}': {'found' if keyword in content else 'MISSING!'}")

with open('tools/rmqtt_webui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("✅ File saved")
