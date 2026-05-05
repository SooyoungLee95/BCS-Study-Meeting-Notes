"""
환경 설정 - .env 파일 또는 환경 변수에서 읽음

필요한 환경 변수:
  GOOGLE_SERVICE_ACCOUNT_JSON  : Google 서비스 계정 JSON 파일 경로 (또는 내용)
  CONFLUENCE_BASE_URL          : e.g. https://rgpkorea.atlassian.net
  CONFLUENCE_EMAIL             : Atlassian 계정 이메일
  CONFLUENCE_API_TOKEN         : Atlassian API 토큰
  SLACK_BOT_TOKEN              : xoxb- 형식의 Slack Bot Token
  SLACK_CHANNEL_ID             : 스터디 채널 ID
  DRIVE_ROOT_FOLDER_ID         : 바코스 폴더 ID
  CONFLUENCE_ROOT_PAGE_ID      : 바코스 Confluence 최상위 페이지 ID
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Google Drive
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID", "15mGp9TSV-jYcAQ_nocfUgMosSWlktHDy")
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]

# Confluence
CONFLUENCE_BASE_URL = os.getenv("CONFLUENCE_BASE_URL", "https://rgpkorea.atlassian.net")
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL", "")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "")
CONFLUENCE_ROOT_PAGE_ID = os.getenv("CONFLUENCE_ROOT_PAGE_ID", "5411143700")

# Slack
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C0AFU091DRC")

# 경로 규칙: YYMM (예: 2604 = 2026년 4월)
AUDIO_SUBFOLDER = "음성녹음"
TRANSCRIPT_SUBFOLDER = "음성전사"
MODEL_SUBFOLDER = "models"
