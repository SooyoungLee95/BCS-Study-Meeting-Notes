"""
전체 파이프라인 실행 스크립트

사용법:
  python pipeline.py --year-month 2604 [--skip-transcribe]
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="바코스 스터디 월간 PPT 파이프라인")
    parser.add_argument("--year-month", required=True, help="YYMM 형식 (예: 2604)")
    parser.add_argument("--skip-transcribe", action="store_true",
                        help="음성전사 단계 건너뛰기")
    args = parser.parse_args()
    ym = args.year_month

    if not args.skip_transcribe:
        print(f"[1/2] 음성 전사 시작 ({ym})")
        from transcribe import run as transcribe_run
        try:
            transcribe_run(ym)
        except Exception as e:
            print(f"⚠️  음성 전사 실패: {e}")
            sys.exit(1)
    else:
        print("[1/2] 음성 전사 건너뜀")

    print(f"[2/2] PPT 생성 시작 ({ym})")
    from generate_ppt import run as ppt_run
    ppt_run(ym)
    print("\n✅ 파이프라인 완료!")


if __name__ == "__main__":
    main()
