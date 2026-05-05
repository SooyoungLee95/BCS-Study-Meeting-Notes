# 바코스 스터디 PPT 자동화 스크립트

## 구성

| 파일 | 설명 |
|------|------|
| `pipeline.py` | 전체 파이프라인 실행 (음성전사 → PPT 생성) |
| `transcribe.py` | 음성 전사만 실행 |
| `generate_ppt.py` | PPT 생성만 실행 |
| `drive_utils.py` | Google Drive API 헬퍼 |
| `confluence_utils.py` | Confluence API 헬퍼 |
| `slack_utils.py` | Slack API 헬퍼 (인증 사진 다운로드) |
| `config.py` | 환경 변수 설정 |
| `requirements.txt` | Python 의존성 목록 |

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

프로젝트 루트에 `.env` 파일 생성:

```env
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
CONFLUENCE_BASE_URL=https://rgpkorea.atlassian.net
CONFLUENCE_EMAIL=your@email.com
CONFLUENCE_API_TOKEN=your_api_token
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_ID=C0AFU091DRC
DRIVE_ROOT_FOLDER_ID=15mGp9TSV-jYcAQ_nocfUgMosSWlktHDy
CONFLUENCE_ROOT_PAGE_ID=5411143700
```

## 실행

### 전체 파이프라인 (음성전사 + PPT)
```bash
python pipeline.py --year-month 2604
```

### 음성전사만
```bash
python transcribe.py --year-month 2604
```

### PPT 생성만 (전사 완료 후)
```bash
python pipeline.py --year-month 2604 --skip-transcribe
```

## 파이프라인 흐름

```
Drive 바코스/YYMM/음성녹음/*.m4a
        ↓ (1단계: transcribe.py)
Drive 바코스/models/ggml-large-v3.bin  →  pywhispercpp 전사
        ↓
Drive 바코스/YYMM/음성전사/*.txt
        ↓ (2단계: generate_ppt.py)
Confluence 바코스 하위 YYMM 회의록
Slack C0AFU091DRC 스터디 인증 사진
        ↓
Drive 바코스/YYMM/바코스_스터디_YYMM.pptx
```

## PPT 구성

1. 타이틀 슬라이드
2. 스터디 프로젝트 현황
3. 각 회의 날짜별 슬라이드 (진행 내용 + Insights + 음성전사 미리보기)
4. 음성전사 요약 슬라이드
5. 스터디 인증 사진 슬라이드
