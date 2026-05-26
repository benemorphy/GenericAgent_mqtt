# GenericAgent MQTT - 全服务启动脚本
param([switch]$NoGateway)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Get-Item $root).Parent.FullName
Set-Location $root
$ErrorActionPreference = 'SilentlyContinue'

# 加载 agent.env (JWT 令牌 + 连接凭据)
$envFile = Join-Path $root 'agent.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process')
        }
    }
    Write-Host '[OK] agent.env loaded' -Fore Green
    # 映射 Dashboard 凭据到 MQTT 环境变量（BBSClient 从 MQTT_USERNAME/PASSWORD 读取）
    $env:MQTT_USERNAME = $env:DASHBOARD_USERNAME
    $env:MQTT_PASSWORD = $env:DASHBOARD_PASSWORD
    Write-Host '[OK] MQTT credentials set (dashboard => MQTT_USERNAME)' -Fore Green
} else {
    Write-Host '[!] agent.env not found (JWT tokens missing)' -Fore Yellow
}

# 1. MariaDB
$svc = Get-Service -Name MariaDB -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -eq 'Running') {
    Write-Host '[OK] MariaDB (3306) 已在运行' -Fore Green
} else {
    try { Start-Service MariaDB -ErrorAction Stop; Write-Host '[OK] MariaDB 已启动' -Fore Green }
    catch { Write-Host '[!] MariaDB 未启动' -Fore Red }
}

# 2. Mosquitto (1883)
$mq = Get-Process mosquitto -ErrorAction SilentlyContinue
if ($mq) {
    Write-Host "[OK] Mosquitto (1883) PID=$($mq.Id) 已在运行" -Fore Green
} else {
    Start-Process 'D:\tools\mosquitto\mosquitto.exe' -ArgumentList '-c D:\tools\mosquitto\mosquitto.conf' -WindowStyle Hidden
    Start-Sleep 3
    Write-Host '[OK] Mosquitto 已启动 (1883)' -Fore Green
}

# 3. simphtml_rs (8901)
$p = Get-NetTCPConnection -LocalPort 8901 -ErrorAction SilentlyContinue
if ($p) { Write-Host '[OK] simphtml_rs (8901) 已在运行' -Fore Green }
else {
    $exe = Join-Path $root 'tools\simphtml_rs\target\release\simphtml_rs.exe'
    if (Test-Path $exe) { Start-Process $exe -ArgumentList '--serve --port 8901' -WindowStyle Hidden; Start-Sleep 2; Write-Host '[OK] simphtml_rs 已启动 (8901)' -Fore Green }
    else { Write-Host '[!] simphtml_rs 未编译，跳过' -Fore Yellow }
}

# 4. rmqtt_webui_rs (8900) — 强制重启以使用正确的 MQTT 凭据
$p = Get-NetTCPConnection -LocalPort 8900 -ErrorAction SilentlyContinue
if ($p) {
    Write-Host '[..] rmqtt Web UI (8900) 存在，重启以应用dashboard凭据...' -Fore Yellow
    $old = Get-Process -Name "rmqtt_webui_rs" -ErrorAction SilentlyContinue
    if ($old) { Stop-Process -Id $old.Id -Force; Start-Sleep 2 }
}
$exe = Join-Path $root 'tools\rmqtt_webui_rs\target\debug\rmqtt_webui_rs.exe'
if (Test-Path $exe) { Start-Process $exe -WindowStyle Hidden; Start-Sleep 2; Write-Host '[OK] rmqtt Web UI 已启动 (8900)' -Fore Green }
else { Write-Host '[!] rmqtt_webui_rs debug未编译，跳过' -Fore Yellow }

# 5. md_server_rs (8899)
$p = Get-NetTCPConnection -LocalPort 8899 -ErrorAction SilentlyContinue
if ($p) { Write-Host '[OK] MD Server (8899) 已在运行' -Fore Green }
else {
    $exe = Join-Path $projectRoot 'GA_tools\md_server_rs\target\release\md_server_rs.exe'
    if (Test-Path $exe) { 
        $docsDir = Join-Path $projectRoot 'docs'
        Start-Process $exe -ArgumentList @('8899', $docsDir) -WindowStyle Hidden
        Start-Sleep 2
        if (Get-NetTCPConnection -LocalPort 8899 -ErrorAction SilentlyContinue) {
            Write-Host '[OK] MD Server 已启动 (8899)' -Fore Green
        } else {
            Write-Host '[!] MD Server 启动可能失败，请检查' -Fore Yellow
        }
    }
    else { Write-Host '[!] md_server_rs 未编译，跳过' -Fore Yellow }
}

# 6. BoardService RS
$exe = Join-Path $root 'mqtt_bbs\tools\board_service_rs\target\release\board_service_rs.exe'
if (Test-Path $exe) {
    $pw = [Environment]::GetEnvironmentVariable('DB_PASSWORD','Process')
    Start-Process $exe -ArgumentList "--db-url ""mysql://root:$pw@127.0.0.1/mqtt_bbs""" -WindowStyle Hidden
    Start-Sleep 3; Write-Host '[OK] BoardService RS 已启动' -Fore Green
} else { Write-Host '[!] BoardService RS 未编译，跳过' -Fore Yellow }

# 7. Gateway (8000) — 强制重启以使用正确的 MQTT 凭据
if (-not $NoGateway) {
    $p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host '[..] Gateway (8000) 旧实例存在，重启以应用MQTT凭据...' -Fore Yellow
        # 找到旧Gateway进程并杀掉
        $oldPy = Get-Process | Where-Object { $_.ProcessName -eq 'python' -and $_.CommandLine -like '*gateway*' } | Select-Object -First 1
        if ($oldPy) { Stop-Process -Id $oldPy.Id -Force; Start-Sleep 2 }
    }
    $py = Join-Path $projectRoot '.venv\Scripts\python.exe'
    Start-Process $py -ArgumentList '-m frontends.gateway.main' -WorkingDirectory (Join-Path $projectRoot 'GA') -WindowStyle Hidden
    Start-Sleep 5
    try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/login' -UseBasicParsing -TimeoutSec 3; Write-Host '[OK] Gateway 已启动 (http://localhost:8000)' -Fore Green }
    catch { Write-Host '[!] Gateway 启动可能失败，请检查' -Fore Red }
}

# 8. Default WorkerAgent — 使用脚本文件（避免 inline -c 转义问题）
Write-Host '[..] 启动默认 WorkerAgent...' -Fore Yellow
$py = Join-Path $projectRoot '.venv\Scripts\python.exe'
$workerScript = Join-Path $root 'tools\start_worker.py'
if (Test-Path $workerScript) {
    Start-Process $py -ArgumentList $workerScript -WorkingDirectory $root -WindowStyle Hidden
    Start-Sleep 3
    # 确认MQTT连接数增加了
    try {
        $b = Invoke-WebRequest -Uri 'http://127.0.0.1:8900/api/broker' -UseBasicParsing -TimeoutSec 2
        Write-Host "[OK] 默认 WorkerAgent 已启动 (MQTT connections=$(($b.Content | ConvertFrom-Json).connections))" -Fore Green
    } catch {
        Write-Host '[OK] 默认 WorkerAgent 已启动' -Fore Green
    }
} else {
    Write-Host "[!] WorkerAgent 脚本未找到: $workerScript" -Fore Red
}

Write-Host ''
Write-Host '===============================' -Fore Cyan
Write-Host '  Service Summary' -Fore Cyan
Write-Host '===============================' -Fore Cyan
$services = @(
    @{n='Gateway';       p=8000;  u='http://localhost:8000'}
    @{n='Mosquitto';     p=1883;  u='mqtt://127.0.0.1:1883'}
    @{n='MariaDB';      p=3306;  u='mysql://127.0.0.1:3306'}
    @{n='simphtml_rs';  p=8901;  u='http://localhost:8901'}
    @{n='rmqtt Web UI'; p=8900;  u='http://localhost:8900'}
    @{n='MD Server';    p=8899;  u='http://localhost:8899'}
    @{n='BoardService'; p=$null; u='MQTT BBS'}
)
foreach ($s in $services) {
    if ($s.p) {
        $t = try { (Get-NetTCPConnection -LocalPort $s.p -ErrorAction Stop).State } catch { 'OFF' }
        $c = if ($t -eq 'Listen') { 'Green' } elseif ($t -eq 'OFF') { 'Red' } else { 'Yellow' }
        Write-Host ("  {0,-15} port {1,5}  [{2}]  {3}" -f $s.n, $s.p, $t, $s.u) -Fore $c
    } else {
        Write-Host ("  {0,-15}           [ACTIVE] {1}" -f $s.n, $s.u) -Fore Green
    }
}
Write-Host '===============================' -Fore Cyan
Write-Host ''
Write-Host '  fsapp.py: python frontends\fsapp.py' -Fore Gray
Write-Host '  Gateway:  http://localhost:8000' -Fore Gray
Write-Host ''
