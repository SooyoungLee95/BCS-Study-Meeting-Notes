"""
음성 전사 스크립트

사용법:
  python transcribe.py --year-month 2604

동작:
  1. Google Drive 바코스/YYMM/음성녹음/ 에서 오디오 파일 다운로드
  2. 바코스/models/ggml-large-v3.bin (GGML Whisper 모델) 다운로드 (캐시)
  3. pywhispercpp 로 음성 전사
  4. 전사 결과를 바코스/YYMM/음성전사/ 에 텍스트 파일로 업로드
"""

import argparse
import os
import tempfile
from pathlib import Path

from drive_utils import (
    get_drive_service,
    find_or_create_folder,
    list_files_in_folder,
    download_file,
    upload_file,
)
from config import DRIVE_ROOT_FOLDER_ID, AUDIO_SUBFOLDER, TRANSCRIPT_SUBFOLDER, MODEL_SUBFOLDER

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".mp4", ".ogg", ".flac"}


def get_ggml_model_path(service, cache_dir: str) -> str:
    """Drive의 models 폴더에서 GGML 모델을 로컬에 캐싱"""
    models_folder_id = _find_subfolder(service, DRIVE_ROOT_FOLDER_ID, MODEL_SUBFOLDER)
    model_files = list_files_in_folder(service, models_folder_id)
    ggml_files = [f for f in model_files if f["name"].endswith(".bin")]
    if not ggml_files:
        raise FileNotFoundError("Drive models/ 폴더에 .bin 모델 파일이 없습니다")

    model_file = ggml_files[0]
    local_model = os.path.join(cache_dir, model_file["name"])
    if not os.path.exists(local_model):
        print(f"모델 다운로드 중: {model_file['name']} ...")
        download_file(service, model_file["id"], local_model)
    else:
        print(f"모델 캐시 사용: {local_model}")
    return local_model


def _find_subfolder(service, parent_id: str, name: str) -> str:
    from googleapiclient.errors import HttpError
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        f" and '{parent_id}' in parents and trashed=false"
    )
    results = service.files().list(q=query, fields="files(id,name)").execute()
    files = results.get("files", [])
    if not files:
        raise FileNotFoundError(f"'{name}' 폴더를 찾을 수 없습니다 (parent: {parent_id})")
    return files[0]["id"]


def transcribe_file(model_path: str, audio_path: str) -> str:
    """pywhispercpp + GGML large-v3 모델로 음성 전사"""
    from pywhispercpp.model import Model
    model = Model(model_path)
    segments = model.transcribe(audio_path)
    return "\n".join(s.text for s in segments)


def run(year_month: str):
    service = get_drive_service()

    # Drive 폴더 경로 탐색
    month_folder_id = _find_subfolder(service, DRIVE_ROOT_FOLDER_ID, year_month)
    audio_folder_id = _find_subfolder(service, month_folder_id, AUDIO_SUBFOLDER)
    transcript_folder_id = find_or_create_folder(service, TRANSCRIPT_SUBFOLDER, month_folder_id)

    audio_files = [
        f for f in list_files_in_folder(service, audio_folder_id)
        if Path(f["name"]).suffix.lower() in AUDIO_EXTENSIONS
    ]
    print(f"오디오 파일 {len(audio_files)}개 발견")

    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = get_ggml_model_path(service, tmpdir)

        for audio_meta in audio_files:
            stem = Path(audio_meta["name"]).stem
            local_audio = os.path.join(tmpdir, audio_meta["name"])
            transcript_name = stem + ".txt"

            print(f"다운로드: {audio_meta['name']}")
            download_file(service, audio_meta["id"], local_audio)

            print(f"전사 중: {audio_meta['name']}")
            text = transcribe_file(model_path, local_audio)

            local_transcript = os.path.join(tmpdir, transcript_name)
            with open(local_transcript, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"업로드: {transcript_name}")
            upload_file(
                service, local_transcript, transcript_name,
                transcript_folder_id, "text/plain"
            )
            print(f"완료: {transcript_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="음성 전사 파이프라인")
    parser.add_argument("--year-month", required=True, help="YYMM 형식 (예: 2604)")
    args = parser.parse_args()
    run(args.year_month)
