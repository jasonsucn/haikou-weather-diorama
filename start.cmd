@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动「海口 · 气象微缩城市」…
echo.
echo [1] 仅本机访问  (http://127.0.0.1:8787)
echo [2] 本机 + 手机/局域网访问  (需要电脑和手机在同一 WiFi)
echo.
choice /c 12 /n /m "请选择 1 或 2："
if errorlevel 2 goto lan
if errorlevel 1 goto local

:lan
start "haikou-weather-server" /min cmd /c "set HOST=0.0.0.0&& node server.mjs"
timeout /t 2 >nul
start "" "http://127.0.0.1:8787"
echo 服务已启动（局域网模式）：http://127.0.0.1:8787
echo 手机访问：查看本机 IPv4 地址（ipconfig），用 http://<本机IP>:8787
echo 例如：http://192.168.3.113:8787
echo 关闭本窗口不会停止服务；如需停止，请关闭最小化的 haikou-weather-server 窗口。
pause
exit /b

:local
start "haikou-weather-server" /min cmd /c "node server.mjs"
timeout /t 2 >nul
start "" "http://127.0.0.1:8787"
echo 服务已启动：http://127.0.0.1:8787
echo 关闭本窗口不会停止服务；如需停止，请关闭最小化的 haikou-weather-server 窗口。
pause
