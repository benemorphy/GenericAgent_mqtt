import subprocess, time, urllib.request, json, os
from pathlib import Path

mf_root = Path(r"D:\open_claw_agent\MindFlow")
py_path = mf_root / ".venv" / "Scripts" / "python.exe"
os.chdir(str(mf_root))

# Kill & restart
for line in subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=5).stdout.splitlines():
    if "9900" in line and "LISTENING" in line:
        subprocess.run(["taskkill", "/F", "/PID", line.strip().split()[-1]], capture_output=True, timeout=3)
time.sleep(1)

proc = subprocess.Popen(
    [str(py_path), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9900"],
    cwd=str(mf_root), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NO_WINDOW
)
time.sleep(4)

base = "http://127.0.0.1:9900"

# Health
with urllib.request.urlopen(base + "/health", timeout=5) as r:
    print(f"Health: {r.status}")

# Generate genetic courseware
req = urllib.request.Request(
    base + "/api/v1/courseware/generate",
    data=json.dumps({"topic": "遗传与变异现象", "subject": "biology", "grade": "8"}).encode(),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read())
    cw_id = result["courseware_id"]
    print(f"Generated: {cw_id}, modules={result.get('modules',0)}")

# Get data for audit
time.sleep(2)
with urllib.request.urlopen(base + "/api/v1/courseware/" + cw_id, timeout=5) as r:
    cw_data = json.loads(r.read())

modules = cw_data.get("modules", [])
abt_parts = set()
img_blocks = 0
for m in modules:
    if m.get("abt_part"): abt_parts.add(m["abt_part"])
    for c in (m.get("content") or []):
        if isinstance(c, dict) and c.get("type") == "image":
            img_blocks += 1

total_min = sum(m.get("estimated_minutes", 0) for m in modules)
concepts_count = len(cw_data.get("concepts", []))
relations_count = len(cw_data.get("relations", []))

print(f"\n=== 审计结果 ===")
print(f"S1 ABT完整: {abt_parts} (需含and/but/therefore)")
print(f"S2 模块数: {len(modules)} (需≥5)")
print(f"S3 总时长: {total_min}min (需≤15)")
print(f"C1 concepts: {concepts_count} (需≥5)")
print(f"C2 relations: {relations_count} (需≥3)")
print(f"V1 ImageContent: {img_blocks} (需≥70%模块有)")

# Git
subprocess.run(["git", "add", "app/skill/phases/courseware.py", "app/engine/ai/ga_provider.py"], cwd=str(mf_root))
r = subprocess.run(["git", "commit", "-m", "refactor: CoursewarePhase 6-module ABT + concepts/relations pass-through"], cwd=str(mf_root), capture_output=True, text=True, timeout=10)
print(f"\nGit: {r.stdout[:100]}")
r = subprocess.run(["git", "push"], cwd=str(mf_root), capture_output=True, text=True, timeout=60)
print(f"Push: {r.returncode}")
