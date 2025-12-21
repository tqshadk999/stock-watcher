name: US Stock BB Intraday Scanner

on:
  # ⏰ 자동 실행 (한국시간 기준)
  # 07:00 KST → 22:00 UTC (전날)
  # 11:00 KST → 02:00 UTC
  # 21:00 KST → 12:00 UTC
  schedule:
    - cron: '0 22 * * 1-5'
    - cron: '0 2 * * 1-5'
    - cron: '0 12 * * 1-5'

  # ▶️ GitHub Actions에서 수동 실행
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest

    timeout-minutes: 20

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run stock scanner
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          CHAT_ID: ${{ secrets.CHAT_ID }}
          PYTHONPATH: ${{ github.workspace }}
          # 수동 실행이면 1, 스케줄이면 0
          FORCE_NOTIFY: ${{ github.event_name == 'workflow_dispatch' && '1' || '0' }}
        run: |
          python app/cloud_scan_once.py
