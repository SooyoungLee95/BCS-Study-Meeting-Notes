"""Slack 유틸리티 - 스터디 인증 사진 다운로드"""

import os
import re
from pathlib import Path

from slack_sdk import WebClient

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID


def get_client():
    return WebClient(token=SLACK_BOT_TOKEN)


def fetch_study_photos(year_month: str, output_dir: str) -> list[str]:
    """
    year_month: 'YYMM' 형식 (예: '2604')
    스터디 날짜 메시지에서 이미지 파일만 다운로드하고 로컬 경로 목록 반환
    """
    client = get_client()
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # YYMM → 연도/월 파싱
    yy, mm = int(year_month[:2]) + 2000, int(year_month[2:])

    # 해당 월 시작/종료 Unix timestamp
    import calendar, time, datetime
    start_dt = datetime.datetime(yy, mm, 1)
    end_dt = datetime.datetime(yy, mm, calendar.monthrange(yy, mm)[1], 23, 59, 59)
    oldest = str(start_dt.timestamp())
    latest = str(end_dt.timestamp())

    result = client.conversations_history(
        channel=SLACK_CHANNEL_ID,
        oldest=oldest,
        latest=latest,
        limit=200,
    )

    photo_paths = []
    for msg in result.get("messages", []):
        for f in msg.get("files", []):
            if f.get("mimetype", "").startswith("image/"):
                file_id = f["id"]
                filename = f.get("name", f"{file_id}.png")
                # safe filename
                safe_name = re.sub(r"[^\w.\-]", "_", filename)
                dest = os.path.join(output_dir, safe_name)
                _download_slack_file(client, f["url_private"], dest)
                photo_paths.append(dest)

    return photo_paths


def _download_slack_file(client: WebClient, url: str, dest: str):
    import requests
    headers = {"Authorization": f"Bearer {client.token}"}
    resp = requests.get(url, headers=headers, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
