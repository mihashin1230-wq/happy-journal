@echo off
cd /d "%~dp0"
echo Flask 설치 확인 중...
pip install -r requirements.txt -q
echo.
echo 일기장 시작합니다 → http://127.0.0.1:5000
echo 종료하려면 이 창에서 Ctrl+C를 누르세요.
echo.
python app.py
pause
