<#
.SYNOPSIS
  定期整理 temp\model_responses\ 目录
.DESCRIPTION
  用法:
    .\scripts\cleanup_model_responses.ps1           → 归档超过30天的日志
    .\scripts\cleanup_model_responses.ps1 -DryRun   → 预览，只看不做

  设置每周自动执行:
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
      -Argument "-NoProfile -File D:\open_claw_agent\GenericAgent\scripts\cleanup_model_responses.ps1"
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 09:00
    Register-ScheduledTask -TaskName "GA_CleanupModelResponses" -Action $action -Trigger $trigger
#>

param([switch]$DryRun)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ModelDir = Join-Path $ProjectRoot "temp\model_responses"
$ArchiveDir = Join-Path $ModelDir "archive"
$RetentionDays = 30
$LogFile = Join-Path $ProjectRoot "temp\cleanup_model_responses.log"

$log = @("[$(Get-Date -Format 'yyyy-MM-dd HH:mm')] start")
if ($DryRun) { $log += "  [Dry-Run]" }

if (-not (Test-Path $ModelDir)) { $log += "  [ERROR] no dir"; $log|Out-File $LogFile -Encoding utf8; return }

$files = Get-ChildItem $ModelDir -Filter "model_responses_*.txt" | Sort-Object LastWriteTime
$cutoff = (Get-Date).AddDays(-$RetentionDays)
$oldFiles = $files | Where-Object { $_.LastWriteTime -lt $cutoff }
$recentFiles = $files | Where-Object { $_.LastWriteTime -ge $cutoff }

$log += "  Total:$($files.Count) Keep:$($recentFiles.Count) Archive:$($oldFiles.Count)"
if ($oldFiles.Count -eq 0) { $log += "  Nothing"; $log|Out-File $LogFile -Encoding utf8; return }

if ($DryRun) {
    $log += "  -- To archive --"
    foreach ($f in $oldFiles) {
        $age = [math]::Round(((Get-Date)-$f.LastWriteTime).TotalDays,1)
        $size = [math]::Round($f.Length/1KB,1)
        $log += "    [$age d] $($f.Name) ($size KB)"
    }
    $log|Out-File $LogFile -Encoding utf8; $log -join "`n"; return
}

New-Item $ArchiveDir -ItemType Directory -Force | Out-Null
$moved=0; $sz=0
foreach ($f in $oldFiles) {
    Move-Item -Path $f.FullName -Destination (Join-Path $ArchiveDir $f.Name) -Force
    $moved++; $sz+=$f.Length
    $log += "  OK: $($f.Name)"
}
$mb = [math]::Round($sz/1MB,2)
$log += "  Done: $moved files ($mb MB)"
$log|Out-File $LogFile -Encoding utf8
Write-Host "Done. Log: $LogFile"
