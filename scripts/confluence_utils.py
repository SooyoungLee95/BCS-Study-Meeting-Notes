"""Confluence 유틸리티"""

import requests
from requests.auth import HTTPBasicAuth

from config import CONFLUENCE_BASE_URL, CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN


def _auth():
    return HTTPBasicAuth(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)


def get_page(page_id: str) -> dict:
    url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}"
    params = {"expand": "body.storage,version,title"}
    resp = requests.get(url, auth=_auth(), params=params)
    resp.raise_for_status()
    return resp.json()


def get_child_pages(page_id: str) -> list[dict]:
    url = f"{CONFLUENCE_BASE_URL}/wiki/rest/api/content/{page_id}/child/page"
    results = []
    start = 0
    limit = 50
    while True:
        resp = requests.get(
            url, auth=_auth(), params={"start": start, "limit": limit, "expand": "version"}
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if data.get("size", 0) < limit:
            break
        start += limit
    return results


def get_page_markdown(page_id: str) -> str:
    """페이지 내용을 간단한 텍스트로 반환 (storage XML 파싱)"""
    page = get_page(page_id)
    # storage format에서 테이블 텍스트 추출 (간단 파싱)
    import re
    html = page.get("body", {}).get("storage", {}).get("value", "")
    # 태그 제거
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text
