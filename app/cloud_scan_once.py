# app/cloud_scan_once.py
from app.telegram import send_message
from app.main import run

# 🔍 Actions 환경 테스트
send_message("✅ GitHub Actions Telegram 연결 테스트")

# 📈 스캐너 실행
run()
