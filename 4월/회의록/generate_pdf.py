#!/usr/bin/env python3
"""바코스 스터디 2026년 4월 월간 회의록 PDF 생성"""

import os
import json
import re
import time
import functools
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── 폰트 (WenQuanYi Zen Hei – Korean/CJK 지원) ────────────────────────────
_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
pdfmetrics.registerFont(TTFont("K",  _FONT, subfontIndex=0))
pdfmetrics.registerFont(TTFont("KB", _FONT, subfontIndex=0))

# ── 색상 ─────────────────────────────────────────────────────────────────
C_NAVY  = colors.HexColor("#1E3A6E")
C_BLUE  = colors.HexColor("#2D4A8A")
C_LBLUE = colors.HexColor("#4A7CBF")
C_BG    = colors.HexColor("#E8F0FB")
C_LGRAY = colors.HexColor("#F5F5F5")
C_DGRAY = colors.HexColor("#555555")

# ── 스타일 ────────────────────────────────────────────────────────────────
def _s(name, **kw):
    base = dict(fontName="K", fontSize=10, textColor=colors.black,
                spaceAfter=4, leading=16)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = {
    "title":    _s("title",  fontName="KB", fontSize=28, textColor=C_BLUE,
                   alignment=TA_CENTER, spaceAfter=8),
    "sub":      _s("sub",    fontName="K",  fontSize=16, textColor=C_LBLUE,
                   alignment=TA_CENTER, spaceAfter=6),
    "date_lbl": _s("dl",     fontName="K",  fontSize=11, textColor=C_DGRAY,
                   alignment=TA_CENTER, spaceAfter=4),
    "sec":      _s("sec",    fontName="KB", fontSize=17, textColor=C_BLUE,
                   spaceAfter=10, spaceBefore=14),
    "h3":       _s("h3",     fontName="KB", fontSize=12, textColor=C_LBLUE,
                   spaceAfter=6, spaceBefore=10),
    "body":     _s("body"),
    "b1":       _s("b1",     fontSize=10, spaceAfter=3, leading=15, leftIndent=14),
    "b2":       _s("b2",     fontSize=9,  textColor=C_DGRAY, spaceAfter=3,
                   leading=14, leftIndent=28),
    "note":     _s("note",   fontSize=9,  textColor=C_DGRAY, leading=14),
    "toc":      _s("toc",    fontSize=11, spaceAfter=6, leading=18),
    "pt":       _s("pt",     fontName="KB", fontSize=13, textColor=C_BLUE,
                   spaceAfter=6, spaceBefore=8),
    "pl":       _s("pl",     fontSize=8,  textColor=C_DGRAY, alignment=TA_CENTER),
}

# ── 헬퍼 ─────────────────────────────────────────────────────────────────
def hr(thick=1):
    return HRFlowable(width="100%", thickness=thick,
                      color=C_LBLUE if thick == 1 else colors.lightgrey,
                      spaceAfter=6)
def sp(h=4):  return Spacer(1, h * mm)
def P(text, style="body"): return Paragraph(text, S[style])
def bullet(text, d=1):
    return Paragraph(("  •  " if d == 2 else "•  ") + text, S["b2" if d==2 else "b1"])

# ── 재시도 데코레이터 ──────────────────────────────────────────────────────
def retry(max_attempts=3, delay=2, exceptions=(Exception,)):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    wait = delay * (2 ** (attempt - 1))
                    print(f"[retry] {fn.__name__} 실패 (시도 {attempt}/{max_attempts}): {e} → {wait}s 후 재시도")
                    time.sleep(wait)
        return wrapper
    return decorator

# ── 전사본 읽기 ────────────────────────────────────────────────────────────
def load_transcript(base_dir, name):
    """4월/음성전사/{name}.json 을 읽어 타임스탬프 포함 블록 리스트 반환."""
    json_path = os.path.join(base_dir, f"{name}.json")
    if not os.path.exists(json_path):
        return []
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    segments = data.get("segments", [])

    # 한국어 비율 50% 이상인 세그먼트만 선택 후 시간 근접한 것 병합
    clean = []
    for seg in segments:
        t = seg["text"].strip()
        if len(t) < 10:
            continue
        kor = sum(1 for c in t if "가" <= c <= "힣")
        total = len(t.replace(" ", ""))
        if total and kor / total >= 0.50:
            clean.append((seg["start"], t))

    if not clean:
        return []

    merged, cur_ts, cur_parts = [], clean[0][0], [clean[0][1]]
    for i in range(1, len(clean)):
        ts, t = clean[i]
        if ts - clean[i - 1][0] < 6:
            cur_parts.append(t)
        else:
            block = " ".join(cur_parts)
            if len(block) >= 15:
                merged.append((cur_ts, block))
            cur_ts, cur_parts = ts, [t]
    if cur_parts:
        block = " ".join(cur_parts)
        if len(block) >= 15:
            merged.append((cur_ts, block))
    return merged

# ── 데이터 ────────────────────────────────────────────────────────────────
MEMBERS = [
    ("이수영", "Sooyoung Lee"),
    ("유민우",  "Minwoo Yoo"),
    ("이준영",  "Joonyoung Lee"),
    ("권종범",  "Jongbeom Kwon"),
    ("이선용",  "Sunyong Lee"),
]

RECORDINGS = [
    ("4/7",  "바코스 4-7.m4a",  "28.3 MB"),
    ("4/21", "바코스 4-21.m4a", "17.1 MB"),
]

SESSIONS = [
    {
        "date": "4월 7일 (화)",
        "has_rec": True,
        "transcript_name": "바코스 4-7",
        "progress": [
            ("이수영",
             "Anthropic courses 완강\nMCP server client 구현",
             "오이 포커 멀티 플레이 완성\n(다음 주 같이 플레이)"),
            ("유민우",
             "오이 포커 1대1 완성",
             "오이 포커 멀티 플레이 완성\n(다음 주 같이 플레이)"),
            ("이준영",
             "Claude Code 원격 서버 구축\n3D 프린터 모델 에디터 crash reporter\n모서리 부드럽게 처리",
             "디버깅 도구 추가\nCrash reporter 디테일화\n모델 에디터 검증 도구"),
            ("권종범",
             "Klaf 에이전트 빌더 플러그인 구현\nMarklas transform 기능 추가",
             "Atlassian MCP 제작\nKlaf 고도화"),
            ("이선용",
             "포모도로 고도화 중 토큰 소진",
             "프리셀 시작"),
        ],
        "insights": [
            "프롬프트 사용량 줄이는 방법 시도 중",
            "클로드 이미지 파일 디버깅 한계",
            ["HTML/코드 문서로 변환 시 이해도 향상"],
            "이준영 사업 모델 공유",
            "Klaf(에이전트 오케스트레이션 프레임워크) 소개",
            [
                "에이전트 분리 실행 효과: 메인 오케스트레이터 컨텍스트 절약",
                "에이전트별 역할에 맞는 스킬만 로드 → 효율적인 스킬 관리",
                "클로드 코드가 에이전트를 스킬처럼 쓰는 경향 해결이 목표",
            ],
        ],
        "slack_images": [
            ("F0AR5SG06A1", "유민우",  "토끼 하트"),
            ("F0AQSQFDTDM", "이수영",  "스터디 화면"),
            ("F0ARLUPAP8R", "이준영",  "CleanShot 화면"),
            ("F0ARM5W0EJD", "유민우",  "스터디 내용"),
        ],
    },
    {
        "date": "4월 14일 (화)",
        "has_rec": False,
        "transcript_name": None,
        "progress": [
            ("이수영",
             "없음",
             "회의록 작성 워크플로우 구성"),
            ("유민우",
             "오이 포커 멀티 플레이 구현\n고도 엔진 공부",
             "오이 포커 멀티 플레이 완성"),
            ("이준영",
             "Claude Code 원격 서버, 3D 프린터 에디터\n(저번 주와 동일)",
             "휴가"),
            ("권종범",
             "Craken - 개인용 Claude Code 마켓플레이스\nKlaf 고도화",
             "Atlassian MCP 제작"),
            ("이선용",
             "프리셀 완료\nSchedule 자동 기능 개발",
             "프리셀 UI 변경\n토큰 소진 시 이어서 하는 방법 고민"),
        ],
        "insights": [
            "Claude schedule 활용: GitHub 이슈 자동 개발",
            [
                "토큰 초기화 주기(1시, 6시)마다 자동 실행",
                "1배치에 토큰 소진 → 다음 배치가 처음부터 작업하는 이슈",
                "작업 현황 기록 방법 모색 중",
            ],
        ],
        "slack_images": [
            ("F0AT2H0BPAM", "이수영",  "스터디 화면"),
            ("F0ASPS76Q74", "이수영",  "선용님 내용 확인"),
            ("F0ATJ4W8R4Y", "이선용",  "이어서 하는 방법"),
            ("F0ATJ4ZGUBA", "이선용",  "설명 화면"),
            ("F0ASTEMB1A8", "이수영",  "리포지토리 선택"),
            ("F0ASLFGB02H", "이선용",  "커밋 결과"),
        ],
    },
    {
        "date": "4월 21일 (화)",
        "has_rec": True,
        "transcript_name": "바코스 4-21",
        "progress": [
            ("이수영",
             "없음",
             "회의록 작성 워크플로우 구성"),
            ("유민우",
             "오이 포커 멀티 플레이 구현\nClaude Design으로 화면 구성",
             "오이 포커 멀티 플레이 완성"),
            ("이준영",
             "3D 프린팅 에디터 crash reporter\n커뮤니티 백엔드 (계정 체계, Outbox 패턴, 보안 감사)",
             "3D 커뮤니티 프론트 (Claude Design)\n백엔드 메인 로직"),
            ("권종범",
             "Klaf 고도화",
             "Atlassian MCP 제작"),
            ("이선용",
             "하네스 공부",
             "프리셀 UI 변경 (Claude Design)\n토큰 소진 이어하기 방법 고민"),
        ],
        "insights": [
            "Claude Design 기능 공유 및 활용 사례 논의",
            "Opus 4.7 동작 방식 변경 공유",
            "Klaf 고도화 논의",
            [
                ".claude 루트 수백 개 스킬 정의 시 메인 에이전트의 스킬 선택 판단력 저하",
                "에이전트별 스킬 계층화: python → python web → django",
                "Sub-agent 전용 스킬을 main agent가 모르도록 격리",
                "책임 상속 구조: python 개발자 → web server 개발자 → django 개발자",
            ],
            "Agent 하네스(Harness) 공부 및 적용 논의",
        ],
        "slack_images": [
            ("F0AU04NARDH", "유민우",  "Claude Design 결과"),
            ("F0AU542SECE", "유민우",  "스터디 화면"),
            ("F0AUB8HNECC", "이선용",  "Claude Design 한도"),
            ("F0AUD716HRC", "이수영",  "접속 문제 화면"),
        ],
    },
]

# ── 커버 페이지 ────────────────────────────────────────────────────────────
def build_cover():
    e = [sp(28)]
    e += [P("바코스 스터디", "title"), sp(2),
          P("월간 활동 보고서", "sub"), sp(6),
          HRFlowable(width="60%", thickness=2, color=C_LBLUE,
                     spaceAfter=8, hAlign="CENTER"),
          P("2026년 4월", "sub"), sp(3),
          P("April 2026  |  #스터디-mgc  |  매주 화요일 점심", "date_lbl"),
          sp(10)]

    # 멤버 테이블
    mdata = [["이름", "영문명", "담당"]] + [[k, e2, "스터디원"] for k, e2 in MEMBERS]
    mt = Table(mdata, colWidths=[38*mm, 58*mm, 34*mm])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C_NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
        ("FONTNAME",      (0,0),(-1,0),  "KB"),
        ("FONTSIZE",      (0,0),(-1,0),  10),
        ("FONTNAME",      (0,1),(-1,-1), "K"),
        ("FONTSIZE",      (0,1),(-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, colors.white]),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("GRID",          (0,0),(-1,-1), 0.5, colors.lightgrey),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ]))
    e.append(mt)
    e += [sp(8),
          HRFlowable(width="80%", thickness=1, color=C_LBLUE,
                     spaceAfter=6, hAlign="CENTER"),
          P("스터디 목표", "h3"),
          bullet("개인별 AI 활용 프로젝트 최소 한 개씩 완성"),
          bullet("AI Agent 활용 능력 향상 (Agent.md, Skills 노하우 공유)"),
          sp(4),
          P("스터디 기간: 2026.02.24 ~ 2026.06.30  |  불참 시 금요일 12:30", "note"),
          sp(4)]

    # 음성녹음 파일 목록
    e.append(P("음성녹음 파일", "h3"))
    rdata = [["날짜", "파일명", "크기"]] + [[d, f, s] for d, f, s in RECORDINGS]
    rt = Table(rdata, colWidths=[20*mm, 100*mm, 25*mm])
    rt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  C_NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0),  colors.white),
        ("FONTNAME",      (0,0),(-1,0),  "KB"),
        ("FONTSIZE",      (0,0),(-1,0),  9),
        ("FONTNAME",      (0,1),(-1,-1), "K"),
        ("FONTSIZE",      (0,1),(-1,-1), 9),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, colors.white]),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("GRID",          (0,0),(-1,-1), 0.5, colors.lightgrey),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
    ]))
    e.append(rt)
    e.append(P("* 음성녹음은 GitHub 레포지토리 4월/음성녹음/ 디렉토리에서 확인할 수 있습니다.", "note"))
    e.append(PageBreak())
    return e

# ── 목차 ─────────────────────────────────────────────────────────────────
def build_toc():
    e = [P("목차", "sec"), hr()]
    for num, title in [
        ("1", "4월 7일   스터디 회의록  (음성녹음 있음)"),
        ("2", "4월 14일 스터디 회의록"),
        ("3", "4월 21일 스터디 회의록  (음성녹음 있음)"),
        ("4", "4월 스터디 캡처 사진 모음"),
    ]:
        e.append(P(f"  {num}.  {title}", "toc"))
    e.append(PageBreak())
    return e

# ── 진행 현황 테이블 ────────────────────────────────────────────────────────
def build_progress(progress):
    cs = ParagraphStyle("cs", fontName="K",  fontSize=9, leading=13)
    hs = ParagraphStyle("hs", fontName="KB", fontSize=9, textColor=colors.white,
                        leading=13, alignment=TA_CENTER)
    header = ["담당자", "지난 주 한 것", "이번 주 계획"]
    rows = [[Paragraph(c, hs if i==0 else cs) for c in row]
            for i, row in enumerate([header] + list(progress))]
    t = Table(rows, colWidths=[24*mm, 74*mm, 74*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), C_NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[C_BG, colors.white]),
        ("GRID",          (0,0),(-1,-1), 0.5, colors.lightgrey),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ("RIGHTPADDING",  (0,0),(-1,-1), 6),
    ]))
    return t

# ── 음성 전사 섹션 ────────────────────────────────────────────────────────
def build_audio_section(transcript_name, base_dir):
    e = [HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4),
         P("음성 녹음 분석", "h3")]
    blocks = load_transcript(base_dir, transcript_name)
    if not blocks:
        e.append(P("전사 파일 없음 또는 인식된 한국어 내용 없음", "note"))
        return e
    e.append(P(f"※ Whisper(tiny) 자동 전사 기반 — 발화 발췌 {len(blocks)}블록 중 상위 20개", "note"))
    e.append(sp(2))
    ts_style = _s("ts", fontSize=8, textColor=C_LBLUE, leading=12)
    for ts, text in blocks[:20]:
        mins, secs = int(ts // 60), int(ts % 60)
        row = Table(
            [[Paragraph(f"[{mins:02d}:{secs:02d}]", ts_style),
              Paragraph(text, S["b1"])]],
            colWidths=[12*mm, None]
        )
        row.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ]))
        e.append(row)
    return e

# ── 세션 페이지 ────────────────────────────────────────────────────────────
def build_session(sess, transcript_base_dir):
    rec_note = "  [음성녹음 있음]" if sess["has_rec"] else ""
    e = [P(f"▌ {sess['date']} 스터디 회의록{rec_note}", "sec"), hr(), sp(2),
         P("진행 현황", "h3"),
         build_progress(sess["progress"]),
         sp(6),
         HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4),
         P("주요 인사이트 및 공유 내용", "h3")]
    for item in sess["insights"]:
        if isinstance(item, list):
            for sub in item: e.append(bullet(sub, d=2))
        else:
            e.append(bullet(item))
    e.append(sp(4))
    if sess["has_rec"]:
        e += build_audio_section(sess["transcript_name"], transcript_base_dir)
    else:
        e += [HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey, spaceAfter=4),
              P("음성 녹음 분석", "h3"),
              P("이 날짜의 음성 녹음 파일이 없습니다.", "note")]
    e += [sp(4),
          P(f"슬랙 캡처 사진: {len(sess['slack_images'])}장 (마지막 페이지 참조)", "note"),
          PageBreak()]
    return e

# ── 사진 모음 페이지 ───────────────────────────────────────────────────────
def build_photos():
    e = [P("4월 스터디 캡처 사진 모음", "sec"), hr(),
         P("슬랙 채널 #스터디-mgc (C0AFU091DRC)에 업로드된 날짜별 캡처 사진 목록입니다.", "note"),
         sp(4)]

    cap_s = ParagraphStyle("cap", fontName="KB", fontSize=9,
                           alignment=TA_CENTER, textColor=C_BLUE)
    for sess in SESSIONS:
        e.append(P(f"▸  {sess['date']}", "pt"))
        imgs = sess["slack_images"]
        rows, row = [], []
        for i, (fid, uploader, caption) in enumerate(imgs):
            cell = Table(
                [[Paragraph(caption, cap_s)],
                 [Paragraph(f"업로더: {uploader}", S["pl"])],
                 [Paragraph(f"ID: {fid}", S["pl"])]],
                colWidths=[54*mm])
            cell.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), C_LGRAY),
                ("BOX",           (0,0),(-1,-1), 1, C_LBLUE),
                ("TOPPADDING",    (0,0),(-1,-1), 10),
                ("BOTTOMPADDING", (0,0),(-1,-1), 10),
                ("ALIGN",         (0,0),(-1,-1), "CENTER"),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ]))
            row.append(cell)
            if len(row) == 3 or i == len(imgs) - 1:
                while len(row) < 3: row.append("")
                rows.append(row); row = []
        grid = Table(rows, colWidths=[60*mm, 60*mm, 60*mm],
                     spaceBefore=3, spaceAfter=6)
        grid.setStyle(TableStyle([
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 3),
            ("RIGHTPADDING",  (0,0),(-1,-1), 3),
        ]))
        e += [grid, sp(3),
              HRFlowable(width="100%", thickness=0.5,
                         color=colors.lightgrey, spaceAfter=4)]
    e += [sp(4),
          P("* 사진 파일 ID는 Slack Files API(https://api.slack.com/methods/files.info)로 다운로드 가능합니다.", "note")]
    return e

# ── 페이지 번호 ────────────────────────────────────────────────────────────
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("K", 8)
    canvas.setFillColor(C_DGRAY)
    canvas.drawCentredString(
        A4[0] / 2, 14 * mm,
        f"바코스 스터디  |  2026년 4월 월간 회의록  |  {canvas.getPageNumber()} 페이지"
    )
    canvas.restoreState()

# ── 메인 ─────────────────────────────────────────────────────────────────
@retry(max_attempts=3, delay=2)
def build_pdf(out, transcript_dir):
    doc = SimpleDocTemplate(
        out, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm,  bottomMargin=22*mm,
        title="바코스 스터디 2026년 4월 월간 회의록",
        author="바코스 스터디",
    )
    story = build_cover() + build_toc()
    for sess in SESSIONS:
        story += build_session(sess, transcript_dir)
    story += build_photos()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(script_dir, "2026-04_바코스_스터디_월간_회의록.pdf")
    # 전사본 디렉토리: 스크립트 기준 ../음성전사/
    transcript_dir = os.path.normpath(os.path.join(script_dir, "../음성전사"))
    print(f"전사본 경로: {transcript_dir}")
    build_pdf(out, transcript_dir)
    print(f"완료: {out}")

if __name__ == "__main__":
    main()
