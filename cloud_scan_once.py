# cloud_scan_once.py
# GitHub Actions에서 "한 번만" 실행되는 엔트리포인트(PC 꺼져도 실행됨)

import os
import traceback
from datetime import datetime

import pytz

from notifier import send_message
from main import init_tickers, combined, check_symbol_and_alert, maybe_send_topn

KST = pytz.timezone("Asia/Seoul")


def run_once():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_TOKEN 또는 CHAT_ID가 비어 있습니다. (GitHub Secrets/ENV 확인)")

    now = datetime.now(KST)

    # ✅ Actions 실행 확인용: 무조건 1회 테스트 메시지 전송
    send_message(
        token,
        chat_id,
        f"✅ *Cloud Watcher 실행됨*\n시간(KST): `{now.strftime('%Y-%m-%d %H:%M:%S')}`",
        parse_mode="Markdown",
    )

    # 티커 로드
    init_tickers()

    # ✅ 예약 시간(08/12/22)에는 TopN도 보냄 (main.py 내부 로직 그대로 사용)
    maybe_send_topn(now)

    # ✅ 조건 스캔(한 번 전체 스캔)
    hit = 0
    for index_name, symbol in combined:
        before = hit
        check_symbol_and_alert(index_name, symbol, now)
        # check_symbol_and_alert가 알림을 보내면 내부에서 last_alert_time 갱신하지만
        # 여기서는 "몇 개 알림"을 정확히 알기 어려워서, 완료 메시지만 보냄(안전)
        # (원하면 check_symbol_and_alert가 True/False 반환하도록 바꿔서 hit 카운트 가능)

    send_message(
        token,
        chat_id,
        f"✅ *Cloud Watcher 종료*\n시간(KST): `{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}`",
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    try:
        run_once()
    except Exception as e:
        token = os.getenv("TELEGRAM_TOKEN")
        chat_id = os.getenv("CHAT_ID")
        err = f"❌ *Cloud Watcher 오류*\n`{e}`\n\n```{traceback.format_exc()}```"
        if token and chat_id:
            send_message(token, chat_id, err[:3800], parse_mode="Markdown")
        raise
