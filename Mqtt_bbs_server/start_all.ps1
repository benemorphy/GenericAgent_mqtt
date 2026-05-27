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
    # 映射 mariadb_password -> DB_PASSWORD (mariadb 密码统一使用该环境变量)
    if (-not $env:DB_PASSWORD) { $env:DB_PASSWORD = $env:mariadb_password }
    Write-Host "[OK] DB_PASSWORD set from mariadb_password" -Fore Green
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

# 4. rmqtt_webui_rs (8900) - 强制重启以使用正确的 MQTT 凭据
$p = Get-NetTCPConnection -LocalPort 8900 -ErrorAction SilentlyContinue
if ($p) {
    Write-Host '[..] rmqtt Web UI (8900) 存在，重启以应用dashboard凭据...' -Fore Yellow
    $old = Get-Process -Name "rmqtt_webui_rs" -ErrorAction SilentlyContinue
    if ($old) { Stop-Process -Id $old.Id -Force; Start-Sleep 2 }
}
$exe = Join-Path $root 'tools\rmqtt_webui_rs\target\release\rmqtt_webui_rs.exe'
if (-not (Test-Path $exe)) {
    $exe = Join-Path $root 'tools\rmqtt_webui_rs\target\debug\rmqtt_webui_rs.exe'
}
if (Test-Path $exe) {
    $env:MQTT_USERNAME = 'dashboard'
    $env:MQTT_PASSWORD = 'eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiZGFzaGJvYXJkIiwgImNsaWVudGlkIjogImRhc2hib2FyZCIsICJ1c2VybmFtZSI6ICJkYXNoYm9hcmQiLCAicm9sZSI6ICJvYnNlcnZlciIsICJleHAiOiAxODEwNTM1NTczLCAiaWF0IjogMTc3ODk5OTU3M30.h_4qJej8QnJ8BXOknx5fF7mBQS2obEH7d6r2sZkMpfA'
    Start-Process -FilePath $exe -WindowStyle Hidden
    Start-Sleep 3
    try { $null = Get-NetTCPConnection -LocalPort 8900 -ErrorAction Stop; Write-Host '[OK] rmqtt Web UI 已启动 (8900)' -Fore Green }
    catch { Write-Host '[!] rmqtt Web UI 启动失败 (8900 端口未监听)' -Fore Red }
}
else { Write-Host '[!] rmqtt_webui_rs debug未编译，跳过' -Fore Yellow }

# 5. md_server_rs (8899)
# Usage: md_server_rs [port] [root_dir]
#   port:     默认 8899
#   root_dir: 默认 ./docs (相对 CWD), 支持绝对/相对路径
$p = Get-NetTCPConnection -LocalPort 8899 -ErrorAction SilentlyContinue
if ($p) {
    Write-Host '[..] MD Server (8899) 存在，重启以刷新目录...' -Fore Yellow
    $old = Get-Process -Name "md_server_rs" -ErrorAction SilentlyContinue
    if ($old) { Stop-Process -Id $old.Id -Force; Start-Sleep 2 }
}
$exe = Join-Path $projectRoot 'GA_tools\md_server_rs\target\release\md_server_rs.exe'
if (-not (Test-Path $exe)) {
    $exe = Join-Path $projectRoot 'GA_tools\md_server_rs\target\debug\md_server_rs.exe'
}
if (Test-Path $exe) {
    # 服务项目根目录 (Mqtt_bbs/docs/ 下文档通过相对路径访问)
    $docsDir = $projectRoot
    Start-Process $exe -ArgumentList @('8899', $docsDir) -WindowStyle Hidden
    Start-Sleep 2
    if (Get-NetTCPConnection -LocalPort 8899 -ErrorAction SilentlyContinue) {
        Write-Host "[OK] MD Server 已启动 (8899) 服务: $docsDir" -Fore Green
    } else {
        Write-Host '[!] MD Server 启动可能失败，请检查' -Fore Yellow
    }
}
else { Write-Host '[!] md_server_rs 未编译，跳过 (cargo build --release 编译)' -Fore Yellow }

# 6. BoardService RS
$bs_exe = Join-Path $projectRoot 'Mqtt_bbs_server\tools\board_service_rs\target\release\board_service_rs.exe'
if (-not (Test-Path $bs_exe)) {
    $bs_exe = Join-Path $projectRoot 'Mqtt_bbs_server\tools\board_service_rs\target\debug\board_service_rs.exe'
}
if (Test-Path $bs_exe) {
    $pw = [Environment]::GetEnvironmentVariable('DB_PASSWORD','Process')
    $env:MQTT_USERNAME = 'board-service-rs'
    $env:MQTT_PASSWORD = 'board-service-rs'
    Start-Process $bs_exe -ArgumentList "--db-url ""mysql://root:$pw@127.0.0.1/mqtt_bbs""" -WindowStyle Hidden
    Start-Sleep 3
    try { $null = Get-NetTCPConnection -LocalPort 9100 -ErrorAction SilentlyContinue; Write-Host '[OK] BoardService RS 已启动' -Fore Green }
    catch { Write-Host '[!] BoardService RS 启动可能失败' -Fore Yellow }
} else { Write-Host '[!] BoardService RS 未编译，跳过' -Fore Yellow }

# 7. Gateway (8000) - 强制重启以使用正确的 MQTT 凭据
if (-not $NoGateway) {
    $p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($p) {
        Write-Host '[..] Gateway (8000) 旧实例存在，重启以应用MQTT凭据...' -Fore Yellow
        # 通过端口找到旧Gateway进程并杀掉
        $oldPid = $p.OwningProcess
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        Start-Sleep 2
    }
    $py = Join-Path $projectRoot '.venv\Scripts\python.exe'
    Start-Process $py -ArgumentList '-m frontends.gateway.main' -WorkingDirectory (Join-Path $projectRoot 'GA') -WindowStyle Hidden
    Start-Sleep 5
    try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/login' -UseBasicParsing -TimeoutSec 3; Write-Host '[OK] Gateway 已启动 (http://localhost:8000)' -Fore Green }
    catch { Write-Host '[!] Gateway 启动可能失败，请检查' -Fore Red }
}

# 8. Default WorkerAgent
Write-Host '[..] 启动默认 WorkerAgent...' -Fore Yellow
$py = Join-Path $projectRoot '.venv\Scripts\python.exe'
$workerScript = Join-Path $root 'examples\worker_agent.py'
if (Test-Path $workerScript) {
    Start-Process $py -ArgumentList $workerScript -WorkingDirectory $projectRoot -WindowStyle Hidden
    Start-Sleep 2; Write-Host '[OK] 默认 WorkerAgent 已启动' -Fore Green
} else {
    Write-Host '[!] examples\worker_agent.py 未找到，跳过 WorkerAgent' -Fore Yellow
}

Write-Host ''
Write-Host '========================================' -Fore Cyan
Write-Host '  Service    Port    Status' -Fore Cyan
Write-Host '  --------   ----    ------' -Fore Cyan
@(
  @{n='Gateway';       p=8000;  u='http://localhost:8000'},
  @{n='Mosquitto';     p=1883;  u='mqtt://127.0.0.1:1883'},
  @{n='MariaDB';      p=3306;  u='mysql://127.0.0.1:3306'},
  @{n='simphtml_rs';  p=8901;  u='http://localhost:8901'},
  @{n='rmqtt Web UI'; p=8900;  u='http://localhost:8900'},
  @{n='MD Server';    p=8899;  u='http://localhost:8899'},
  @{n='BoardService'; p='---'; u='MQTT BBS'; chk='board_service_rs'}
) | ForEach-Object {
  $s = if ($_.chk) { try { if (Get-Process -Name $_.chk -ErrorAction Stop) { 'RUN' } else { 'OFF' } } catch { 'OFF' } } elseif ($_.p -eq '---') { '---' } else { try { $t = Get-NetTCPConnection -LocalPort $_.p -ErrorAction Stop; if ($t.State -eq 'Listen') { 'RUN' } else { '???' } } catch { 'OFF' } };
  $c = if ($s -eq 'RUN') { 'Green' } elseif ($s -eq 'OFF') { 'Red' } else { 'Yellow' };
  Write-Host ('  {0,-14} {1,5}  [{2}]' -f $_.n, ('port ' + $_.p), $s) -Fore $c;
};
Write-Host ''
Write-Host '  fsapp.py: python frontends\fsapp.py' -Fore Gray
Write-Host '========================================' -Fore Cyan

Write-Host ''
Write-Host '按 Enter 关闭所有服务 (Ctrl+C 直接退出)' -Fore Gray
Read-Host

# Cleanup section
Write-Host '[..] 正在关闭所有服务...' -Fore Yellow

# 关 WorkerAgent
$pyProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*worker_agent*' }
foreach ($proc in $pyProcesses) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }

# 关 Gateway
$gwProcesses = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*gateway*' }
foreach ($proc in $gwProcesses) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }

# 关 BoardService
Stop-Process -Name "board_service_rs" -Force -ErrorAction SilentlyContinue

# 关 MD Server
Stop-Process -Name "md_server_rs" -Force -ErrorAction SilentlyContinue

# 关 rmqtt_webui_rs
Stop-Process -Name "rmqtt_webui_rs" -Force -ErrorAction SilentlyContinue

# 关 simphtml_rs
Stop-Process -Name "simphtml_rs" -Force -ErrorAction SilentlyContinue

Write-Host '[OK] 所有服务已关闭' -Fore Green
