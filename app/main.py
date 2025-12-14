# app/main.py
from __future__ import annotations

from app.scanner import scan_once


def run_cloud_once() -> None:
    """
    GitHub Actions에서 호출되는 엔트리 포인트
    """
    scan_once()


# 로컬(PyCharm)에서 직접 실행할 때도 동작하게 함
if __name__ == "__main__":
    run_cloud_once()
