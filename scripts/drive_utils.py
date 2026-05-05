"""Google Drive 유틸리티"""

import io
import os
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from config import GOOGLE_SERVICE_ACCOUNT_JSON, DRIVE_SCOPES


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SERVICE_ACCOUNT_JSON, scopes=DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=creds)


def find_or_create_folder(service, name: str, parent_id: str) -> str:
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        f" and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def list_files_in_folder(service, folder_id: str) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query, fields="files(id,name,mimeType,size)"
    ).execute()
    return results.get("files", [])


def download_file(service, file_id: str, dest_path: str) -> str:
    request = service.files().get_media(fileId=file_id)
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return dest_path


def upload_file(service, local_path: str, name: str, parent_id: str, mime_type: str = None) -> str:
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    meta = {"name": name, "parents": [parent_id]}
    # 동일 이름 파일이 있으면 업데이트
    query = f"name='{name}' and '{parent_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id)").execute()
    existing = results.get("files", [])
    if existing:
        file = service.files().update(
            fileId=existing[0]["id"], media_body=media
        ).execute()
    else:
        file = service.files().create(
            body=meta, media_body=media, fields="id"
        ).execute()
    return file["id"]
