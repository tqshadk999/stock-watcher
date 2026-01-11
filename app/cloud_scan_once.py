from app.main import run
from app.telegram import send_message

if __name__ == "__main__":
    send_message("🚀 주식 스캐너 실행 시작")
    run()

