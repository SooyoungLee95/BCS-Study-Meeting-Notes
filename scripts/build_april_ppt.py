"""
2604 (2026년 4월) 스터디 PPT 로컈 생성 스크립트
Confluence 회의록 데이터를 직접 사용 (API 인증 불필요)
사용법: python build_april_ppt.py [output.pptx]
"""

import os, sys, re, tempfile
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

BRAND_DARK   = RGBColor(0x1A, 0x1A, 0x2E)
BRAND_BLUE   = RGBColor(0x16, 0x21, 0x3E)
BRAND_ACCENT = RGBColor(0x0F, 0x3A, 0x71)
BRAND_LIGHT  = RGBColor(0xE0, 0xE8, 0xF5)
WHITE        = RGBColor(0xFF, 0xFF, 0xFF)
GRAY         = RGBColor(0x88, 0x88, 0x88)
YELLOW       = RGBColor(0xFF, 0xD7, 0x00)

SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

MEETINGS = [
    {
        "date": "4/7",
        "rows": [
            ("이수영", "anthropic courses 수강 (완강) / MCP server client 구현"),
            ("유민우", "오이 포커 1대널 완성"),
            ("이준영", "Claude Code 원격 서버 구축 완료 / 3D 모델 에디터 crash reporter / 모서리 처리"),
            ("권종범", "Klaf 에이전트 빌더 플러그인 구현 / Marklas transform 기능 추가"),
            ("이선용", "포모도로 고도화 중 토큰 소진"),
        ],
        "insights": [
            "프롤프트 사용량 줄이는 방법 시도 중",
            "클로드가 이미지 파일 디버깅은 잘 못함 → HTML 변환으로 이해도 향상",
            "주영님 사업 모델 공유",
            "종범님: 에이전트별 스킬 분리 효과 (메인 컨텍스트 절약, 필요 스킬만 로드)",
            "Klaf 개발 이유: Claude Code가 에이전트를 스킬있듯이 쓰는 경향 → 역할에 맞는 에이전트 개발 유도",
        ],
    },
    {
        "date": "4/14",
        "rows": [
            ("이수영", "없음"),
            ("유민우", "오이 포커 멀티플레이 구현 / Godot 엔진 공부"),
            ("이준영", "Claude Code 원격 서버 구축 / crash reporter / 모서리 처리 (휴가)"),
            ("권종범", "craken 상단팅 Claude Code 마켓플레이스 추가 / klaf 고도화"),
            ("이선용", "프리셀 완료 / schedule 자동 기능 개발"),
        ],
        "insights": [
            "Claude schedule로 GitHub 이슈 글어다가 자동 개발",
            "토큰 초기화 주기(1시, 6시)마다 자동 실행",
            "1배치에 토큰 소진 → 작업 현황 기록 방법 탐색 중",
        ],
    },
    {
        "date": "4/21",
        "rows": [
            ("이수영", "회의록 작성 워크플로우 구성"),
            ("유민우", "오이 포커 멀티플레이 구현 / Claude Design으로 화면 구성"),
            ("이준영", "3D 프린팅 커뮤니티 백엔드 계정체계 / Outbox 패턴 구현 / 보안 감사"),
            ("권종범", "Klaf 고도화"),
            ("이선용", "하네스 공부"),
        ],
        "insights": [
            "클로드 디자인 공유 / Opus 4.7 동작 방식 변경",
            "Klaf: .claude 루트에 스킬 수백개 시 메인 에이전트 선택 어려움 → 계층화 방안",
            "에이전트 체임 상속 구조 검토",
            "에이전트 하네스(Harness) 공부",
        ],
    },
    {
        "date": "4/29",
        "rows": [
            ("이수영", "회의록 워크플로우 구성 / claude routine으로 시도"),
            ("유민우", "오이 포커 멀티플레이 재구현 / 게임엔진 MCP 설계문서"),
            ("이준영", "3D 프린팅 커뮤니티 백엔드 메인 로직 / MCP 서버 구현"),
            ("권종범", "codi 구조 확인 / Claude Agent SDK + Slack 병합"),
            ("이선용", "하네스 공부"),
        ],
        "insights": [
            "오이포커 멀티 전환 실패 → 전면 재시작 / 게임엔진 MCP 활용",
            "mumcp: 필요 기능만 묶은 커스텀 MCP / 버스+날씨 퇴근 안내 루틴 목표",
            "claude simplify 조건 설정 가능 (미커밋 변경사항, 브랜치 등)",
            "하네스: 설정에 따라 성능 차이 큼 / 결과 지시, 방법 지시 X",
        ],
    },
]


def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def t(slide, text, l, top, w, h, sz=14, bold=False, color=WHITE, align=PP_ALIGN.LEFT, wrap=True):
    box = slide.shapes.add_textbox(l, top, w, h)
    tf = box.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(sz)
    r.font.bold = bold
    r.font.color.rgb = color
    return box


def ns(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def title_slide(prs):
    s = ns(prs)
    bg(s, BRAND_DARK)
    t(s, "BCS 스터디", Inches(1.2), Inches(1.6), Inches(9.5), Inches(1.2),
      sz=52, bold=True, color=YELLOW, align=PP_ALIGN.LEFT)
    t(s, "월간 스터디 요약", Inches(1.2), Inches(2.9), Inches(9.5), Inches(0.9),
      sz=32, color=WHITE, align=PP_ALIGN.LEFT)
    t(s, "2026년 4월 | 2604", Inches(1.2), Inches(3.8), Inches(9.5), Inches(0.7),
      sz=22, color=BRAND_LIGHT, align=PP_ALIGN.LEFT)
    t(s, "AI Agent 활용 능력 향상 스터디 · 매주 화요일 점심 · 2026.02.24~06.30",
      Inches(1.2), Inches(4.75), Inches(9.5), Inches(0.5), sz=15, color=BRAND_LIGHT)
    t(s, "스터디원: 이수영 · 유민우 · 이준영 · 권종범 · 이선용",
      Inches(1.2), Inches(6.5), Inches(9.5), Inches(0.5), sz=14, color=GRAY)


def overview_slide(prs):
    s = ns(prs)
    bg(s, BRAND_BLUE)
    t(s, "스터디 프로젝트 현황", Inches(0.6), Inches(0.2), Inches(11), Inches(0.7),
      sz=30, bold=True, color=YELLOW)
    members = [
        ("💻 이수영", "웹 게임/주식 추천 앱 · MCP 구현 · 회의록 자동화"),
        ("🎮 유민우", "오이 포커 (Godot 멀티플레이어) · 냉장고 관리 앱"),
        ("🖨 이준영", "Chiptune MIDI 장치 · 3D 프린팅 모델 공유 커뮤니티"),
        ("🤖 권종범", "Klaf 에이전트 빌더 · 금칙어 관리 서비스 · Atlassian MCP"),
        ("🃏 이선용", "[웹] 프리셀 · 포모도로 · 하네스 공부"),
    ]
    for i, (name, proj) in enumerate(members):
        y = Inches(1.2) + i * Inches(1.1)
        t(s, name, Inches(0.6), y, Inches(2.8), Inches(1.0), sz=16, bold=True, color=YELLOW)
        t(s, proj, Inches(3.6), y, Inches(9.2), Inches(1.0), sz=14, color=WHITE)


def meeting_slide(prs, meeting, idx, total):
    s = ns(prs)
    bg(s, BRAND_BLUE)
    date_txt = meeting["date"]
    t(s, f"📅 {date_txt} 회의록 ({idx}/{total})",
      Inches(0.5), Inches(0.1), Inches(12), Inches(0.7), sz=26, bold=True, color=YELLOW)
    t(s, "▪ 진행 내용", Inches(0.5), Inches(0.85), Inches(7.6), Inches(0.4),
      sz=13, bold=True, color=BRAND_LIGHT)
    for i, (name, done) in enumerate(meeting["rows"]):
        y = Inches(1.25) + i * Inches(1.0)
        t(s, name, Inches(0.6), y, Inches(2.0), Inches(0.9), sz=13, bold=True, color=YELLOW)
        short = done[:72] + "…" if len(done) > 72 else done
        t(s, short, Inches(2.8), y, Inches(5.2), Inches(0.9), sz=12, color=WHITE)
    t(s, "💡 Insights", Inches(8.4), Inches(0.85), Inches(4.4), Inches(0.4),
      sz=13, bold=True, color=BRAND_LIGHT)
    ins_y = Inches(1.25)
    for ins in meeting["insights"][:5]:
        short = ins[:68] + "…" if len(ins) > 68 else ins
        t(s, f"• {short}", Inches(8.4), ins_y, Inches(4.5), Inches(0.85), sz=10, color=BRAND_LIGHT)
        ins_y += Inches(0.88)


def summary_slide(prs):
    s = ns(prs)
    bg(s, BRAND_DARK)
    t(s, "2026년 4월 스터디 요약", Inches(0.5), Inches(0.2), Inches(12), Inches(0.7),
      sz=28, bold=True, color=YELLOW)
    highlights = [
        ("💻 이수영", "Anthropic API 과정 완강 · MCP 구현 · 회의록 자동화 워크플로우 착수"),
        ("🎮 유민우", "오이 포커 Godot 멀티플레이어 재구현 · Claude Design 화면 구성"),
        ("🖨 이준영", "3D 커뮤니티 백엔드 Outbox패턴+보안감사 · MCP 서버 개발 착수"),
        ("🤖 권종범", "Klaf 에이전트 계층화 · codi 범용화 · Claude Agent SDK+Slack 구조"),
        ("🃏 이선용", "프리셀 완성 → UI 개선 · 하네스(Harness) 심층 공부"),
    ]
    for i, (n, d) in enumerate(highlights):
        y = Inches(1.1) + i * Inches(1.1)
        t(s, n, Inches(0.6), y, Inches(2.8), Inches(1.0), sz=15, bold=True, color=YELLOW)
        t(s, d, Inches(3.6), y, Inches(9.2), Inches(1.0), sz=13, color=WHITE)


def transcript_slide(prs):
    s = ns(prs)
    bg(s, BRAND_DARK)
    t(s, "🎙 음성 전사 현황", Inches(0.5), Inches(0.2), Inches(12), Inches(0.7),
      sz=28, bold=True, color=YELLOW)
    note = (
        "음성 전사는 scripts/pipeline.py 를 실행하여 자동으로 생성됩니다.\n\n"
        "사용 모델: Google Drive 바코스/models/ggml-large-v3.bin (Whisper large-v3)\n\n"
        "전사 대상 파일 (Drive 바코스/2604/음성녹음/):\n"
        "  • 바코스 4-7.m4a\n  • 바코스 4-21.m4a\n  • 바코스 4-29.m4a\n\n"
        "전사 결과 저장 위치: Drive 바코스/2604/음성전사/*.txt\n\n"
        "실행 방법: cd scripts && python pipeline.py --year-month 2604"
    )
    t(s, note, Inches(1.0), Inches(1.1), Inches(11), Inches(5.5), sz=14, color=BRAND_LIGHT)


def photo_slide(prs, date_str, file_id, idx):
    s = ns(prs)
    bg(s, BRAND_DARK)
    t(s, f"📸 스터디 인증 사진 ({idx}/2) · {date_str}",
      Inches(0.5), Inches(0.1), Inches(12), Inches(0.7), sz=24, bold=True, color=YELLOW)
    t(s, "📷", Inches(5.5), Inches(1.8), Inches(2), Inches(2), sz=72,
      color=RGBColor(0x33, 0x55, 0x88), align=PP_ALIGN.CENTER)
    t(s, f"스터디 인증 사진 · {date_str}",
      Inches(2), Inches(4.0), Inches(9.3), Inches(0.6), sz=18,
      color=RGBColor(0x66, 0x88, 0xAA), align=PP_ALIGN.CENTER)
    t(s, f"Slack 채널: #스터디-mgc · 파일 ID: {file_id}",
      Inches(2), Inches(4.7), Inches(9.3), Inches(0.5), sz=12, color=GRAY, align=PP_ALIGN.CENTER)
    t(s, "pipeline.py 실행 시 실제 사진으로 교체됩니다 (SLACK_BOT_TOKEN 설정 필요)",
      Inches(2), Inches(5.3), Inches(9.3), Inches(0.5), sz=11, color=GRAY, align=PP_ALIGN.CENTER)


def build_ppt(output_path):
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    print("1/7 타이틀 슬라이드..."); title_slide(prs)
    print("2/7 프로젝트 개요 슬라이드..."); overview_slide(prs)
    print("3/7 회의록 슬라이드 (4회)...")
    for i, m in enumerate(MEETINGS):
        meeting_slide(prs, m, i + 1, len(MEETINGS))
    print("4/7 월간 요약 슬라이드..."); summary_slide(prs)
    print("5/7 음성전사 슬라이드..."); transcript_slide(prs)
    print("6/7 인증 사진 슬라이드 (4/21)...")
    photo_slide(prs, "4월 21일", "F0AU542SECE", 1)
    print("7/7 인증 사진 슬라이드 (4/29)...")
    photo_slide(prs, "4월 29일", "F0B0BMR67H9", 2)

    prs.save(output_path)
    import os
    print(f"\n✅ PPT 저장 완료: {output_path} ({os.path.getsize(output_path):,} bytes)")
    return output_path


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/바코스_스터디_2604.pptx"
    build_ppt(out)
