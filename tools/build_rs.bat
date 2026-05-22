@echo off
setlocal
set GCC_EXEC_PREFIX=D:\tools\w64devkit\libexec\gcc\
set LIBRARY_PATH=D:\tools\w64devkit\lib\gcc\x86_64-w64-mingw32\12.2.0;D:\tools\w64devkit\x86_64-w64-mingw32\lib
set PATH=D:\tools\w64devkit\bin;%USERPROFILE%\.cargo\bin;%USERPROFILE%\.rustup\toolchains\stable-x86_64-pc-windows-gnu\lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained;%PATH%

if /I "%1"=="build" (
    cargo build --release
    goto :end
)
if /I "%1"=="debug" (
    cargo build
    goto :end
)

:: 默认: 启动已知二进制
if exist md_server_rs\target\release\md_server_rs.exe (
    start /B "" md_server_rs\target\release\md_server_rs.exe >nul 2>&1
    echo md_server_rs started on :8899
)
if exist simphtml_rs\target\release\simphtml_rs.exe (
    start /B "" simphtml_rs\target\release\simphtml_rs.exe --serve --port 8901 >nul 2>&1
    echo simphtml_rs started on :8901
)
:end
