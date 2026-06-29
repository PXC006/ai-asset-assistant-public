@echo off
chcp 65001
cd /d "%~dp0"

echo ================================
echo AI复利资产助手 - 公开体验版
echo 当前目录：%cd%
echo ================================

if not exist app.py (
echo 错误：当前目录没有 app.py
echo 请确认 start_public_app_8503.bat 放在公开体验版项目根目录
pause
exit /b
)

where python >nul 2>nul
if errorlevel 1 (
echo 错误：未找到 Python，请先安装 Python 并加入 PATH
pause
exit /b
)

if not exist .venv\Scripts\activate.bat (
echo 正在创建虚拟环境...
python -m venv .venv
if errorlevel 1 (
echo 创建虚拟环境失败
pause
exit /b
)
)

call .venv\Scripts\activate
if errorlevel 1 (
echo 激活虚拟环境失败
pause
exit /b
)

echo 正在升级 pip...
python -m pip install --upgrade pip
if errorlevel 1 (
echo 升级 pip 失败，请查看上方错误
pause
exit /b
)

echo 正在安装依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
echo 依赖安装失败，请查看上方错误
pause
exit /b
)

if not exist data (
mkdir data
)

echo.
echo 正在启动公开体验版...
echo 请不要关闭这个窗口
echo 浏览器访问：http://localhost:8503/
echo.

python -m streamlit run app.py --server.port 8503 --server.address localhost

echo.
echo Streamlit 已退出
pause
