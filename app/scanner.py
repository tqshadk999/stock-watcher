# app/scanner.py
from __future__ import annotations

from datetime import datetime, timezone
from app.notifier import send_message


def scan_once() -> None:
    """
    GitHub Actions(예약/수동 실행)에서 '1회 실행'되는 엔트리 포인트.
    지금 단계 목표: "Actions가 실행되면 텔레그램이 무조건 1번 울린다"를 보장.

    ✅ 확인 후:
    - 기존 스캐너 로직(티커 로딩/조건 판단/차트 생성/사진 전송)을
      아래 TODO 영역에 붙여 넣으면 됩니다.
    """
    # UTC와 KST 둘 다 표시 (Actions는 UTC 환경인 경우가 많음)
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    # KST는 UTC+9
    now_kst = datetime.now(timezone.utc).astimezone(
        timezone.utc.__class__(timezone.utc.utcoffset(None))  # dummy, avoid import
    )

    # 위 한 줄이 번거로워서 안전하게 KST 변환은 직접 계산
    # (외부 라이브러리 없이 확실하게)
    from datetime import timedelta
    now_kst2 = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S KST")

    send_message(
        "✅ [Cloud] Stock Watcher 실행됨\n"
        f"- {now_utc}\n"
        f"- {now_kst2}\n"
        "이 메시지가 오면: Secrets/봇/CHAT_ID/Actions 스케줄은 정상입니다."
    )

    # ------------------------------------------------------------
    # TODO: 여기부터 당신의 '실제 스캔 로직'을 붙여 넣으세요.
    #
    # 예시(개념):
    # - 티커 리스트 로드
    # - 가격 데이터 다운로드
    # - 조건 평가
    # - 조건 만족 시 send_message / send_photo 호출
    # ------------------------------------------------------------
