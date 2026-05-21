@echo off
chcp 65001 >nul
REM === GenericAgent Profile Switcher ===
REM Usage: switch_profile.bat [internet|inner|inner_vlm|status]

setlocal enabledelayedexpansion

if "%1"=="" (
    echo Usage: switch_profile.bat [internet^|inner^|inner_vlm^|status]
    echo.
    echo   internet   切换到外网 API 配置 (DeepSeek / OpenAI / Claude)
    echo   inner      切换到内网本地模型配置 (llama-server)
    echo   inner_vlm  切换到内网 VLM 多模态模型配置
    echo   status     查看当前配置状态
    exit /b 1
)

if /i "%1"=="status" (
    python -c "from tools.config_service import ConfigService; cs=ConfigService.instance(); cs.reload(force=False); print('Current profile:', cs.profile_name); print('Config items:', len(cs.get_all()))"
    exit /b %errorlevel%
)

echo Switching to profile: %1
python -c "from tools.config_service import ConfigService; cs=ConfigService.init('%1'); print('Profile:', cs.profile_name); print('Items loaded:', len(cs.get_all()))"

if %errorlevel% equ 0 (
    echo.
    echo [OK] Switched to profile: %1
) else (
    echo.
    echo [FAIL] Profile '%1' not found.
    echo Make sure profiles/%1.py exists with valid configuration.
    echo.
    echo Quick start:
    echo   copy mykey_internet.py profiles/internet.py
    echo   copy mykey_inner.py profiles/inner.py
    echo   copy mykey_inner_vlm.py profiles/inner_vlm.py
)
