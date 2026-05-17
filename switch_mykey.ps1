<#
.SYNOPSIS
  切换 mykey.py 配置：外网(DeepSeek) / 内网(本地llama) / VLM
.DESCRIPTION
# 强制 UTF-8 代码页，确保中文字符/emoji正确显示
chcp 65001 > $null
  用法:
    .\switch_mykey.ps1 inner     → 切到本地模型 (mykey_inner.py → mykey.py)
    .\switch_mykey.ps1 inner_vlm → 切到本地VLM模型 (mykey_inner_vlm.py → mykey.py)
    .\switch_mykey.ps1 internet  → 切到外网API (mykey_internet.py → mykey.py)
    .\switch_mykey.ps1 status    → 查看当前是哪种配置
#>

param(
    [ValidateSet('inner', 'inner_vlm', 'internet', 'status', 'help')]
    [string]$Mode = 'status'
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $ScriptDir "mykey.py"

switch ($Mode) {
    'inner' {
        $source = Join-Path $ScriptDir "mykey_inner.py"
        if (-not (Test-Path $source)) {
            Write-Host "❌ 找不到 mykey_inner.py" -ForegroundColor Red
            exit 1
        }
        Copy-Item -Path $source -Destination $target -Force
        Write-Host "✅ 已切换到 [内网] 本地模型配置 (mykey_inner.py → mykey.py)" -ForegroundColor Green
    }
    'inner_vlm' {
        $source = Join-Path $ScriptDir "mykey_inner_vlm.py"
        if (-not (Test-Path $source)) {
            Write-Host "❌ 找不到 mykey_inner_vlm.py" -ForegroundColor Red
            exit 1
        }
        Copy-Item -Path $source -Destination $target -Force
        Write-Host "✅ 已切换到 [内网VLM] 多模态模型配置 (mykey_inner_vlm.py → mykey.py)" -ForegroundColor Green
    }
    'internet' {
        $source = Join-Path $ScriptDir "mykey_internet.py"
        if (-not (Test-Path $source)) {
            Write-Host "❌ 找不到 mykey_internet.py" -ForegroundColor Red
            exit 1
        }
        Copy-Item -Path $source -Destination $target -Force
        Write-Host "✅ 已切换到 [外网] DeepSeek 配置 (mykey_internet.py → mykey.py)" -ForegroundColor Cyan
    }
    'status' {
        $content = Get-Content $target -Raw -ErrorAction SilentlyContinue
        if (-not $content) {
            Write-Host "❌ 无法读取 mykey.py" -ForegroundColor Red
            exit 1
        }
        if ($content -match 'local-llm') {
            Write-Host "🟢 当前配置: [内网] 本地模型 (127.0.0.1:8080)" -ForegroundColor Green
        } elseif ($content -match 'local-vlm') {
            Write-Host "🟣 当前配置: [内网VLM] 多模态模型 (127.0.0.1:8090)" -ForegroundColor Magenta
        } elseif ($content -match 'deepseek-v4-flash') {
            Write-Host "🔵 当前配置: [外网] DeepSeek V4 Flash" -ForegroundColor Cyan
        } else {
            Write-Host "🟡 当前配置: 未知 (请确认 mykey.py 来源)" -ForegroundColor Yellow
        }
    }
    'help' {
        Write-Host @"
用法: .\switch_mykey.ps1 <Mode>

Mode:
  inner      切换到内网本地模型 (mykey_inner.py → mykey.py)
  inner_vlm  切换到内网VLM多模态模型 (mykey_inner_vlm.py → mykey.py)
  internet   切换到外网 API (mykey_internet.py → mykey.py)
  status     查看当前配置
  help       显示此帮助信息
"@ -ForegroundColor Cyan
    }
}