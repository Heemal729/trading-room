"""글의 금액·수량 노출, 권유·예측 표현, frontmatter를 검사한다
(CLAUDE.md 절대 규칙 3·4, frontmatter 절, compliance 검사 항목 2·3·6).

금액·수량·frontmatter는 ERROR, 권유·예측·보장 표현은 WARN이다.
정규식 검사라 문맥을 읽지 못하므로 WARN 표현은 compliance가 문맥으로 최종 판단한다.
금액·수량 패턴이 의도보다 넓다면 이 파일의 패턴을 PR로 고친다.

사용법: python checks/content_lint.py [글.md ...] [--files-from 목록.txt]
글을 지정하지 않으면 blog/src/content 아래 글 전부를 본다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from postlib import COMMENT_RE, CONTENT_ROOT, FILENAME_RE, Report, collect_paths, load_post, mask, utf8_stdout

DESKS = {"Research", "Strategy", "Risk", "PnL", "BackOffice", "Compliance", "Infra"}
COLLECTIONS = {"journal", "market", "buildlog"}
REQUIRED = ("title", "date", "desk", "aiDrafted", "reviewedBy", "description")
REVIEWER = "구동섭"

NUM = r"\d[\d,]*(?:\.\d+)?"
# (코드, 패턴, 설명)
MONEY = [
    ("money-usd", re.compile(rf"(?:\$|US\$|USD\s?)\s?{NUM}|{NUM}\s?(?:USD|달러)"), "달러 금액"),
    ("money-krw", re.compile(rf"(?:₩|KRW\s?)\s?{NUM}|{NUM}\s?(?:[천만억조]\s?)*(?:원|KRW)(?!화|·|칙|인|래|가)"), "원화 금액"),
    ("shares", re.compile(rf"{NUM}\s?주(?!년|차|간|기|일|말|당|가|식|요|도|째|\s?(?:연속|동안|전|후|만에|사이))"), "주식 수"),
]
ADVICE = [
    ("recommend", re.compile(r"(?:매수|매도|종목)\s?추천|추천\s?(?:종목|합니다|한다|드립|드린)"), "추천"),
    ("solicit", re.compile(r"(?:매수|매도)(?:를|을)?\s?권(?:유|합|한|해)|사세요|파세요|(?:매수|매도|담으)(?:하)?세요|사야\s?한다|팔아야\s?한다"), "매매 권유"),
    ("target-price", re.compile(r"목표\s?주가|목표가(?:\s*[:：]|\s*(?:는|를|로|은)\b|\s*\$?\d)"), "목표가"),
    ("forecast", re.compile(r"(?:오를|상승할|하락할|떨어질|반등할|내릴|올라갈|내려갈|회복할)\s?(?:것|전망|가능성이\s?높)|(?:반등|상승|하락|급등|급락|랠리)\s?(?:예상|전망|기대)"), "방향 예측"),
    ("guarantee", re.compile(r"(?<!불)확실(?!성)|보장|무조건|틀림없|수익(?:을|이)?\s?약속"), "보장성"),
]


def lint_frontmatter(post, report: Report) -> None:
    path = post.path
    m = FILENAME_RE.match(path.name)
    if not m:
        report.add("ERROR", path, 1, "filename", "파일명이 YYYY-MM-DD-<영문-소문자-슬러그>.md 형식이 아님")
    if path.parent.name not in COLLECTIONS:
        report.add("ERROR", path, 1, "collection", f"컬렉션 폴더가 {sorted(COLLECTIONS)} 중 하나가 아님: {path.parent.name}")
    if not post.has_frontmatter:
        report.add("ERROR", path, 1, "frontmatter", "frontmatter 없음")
        return
    fm, at = post.frontmatter, post.fm_lines
    for k in REQUIRED:
        if k not in fm or fm[k] in ("", None):
            report.add("ERROR", path, 1, "frontmatter", f"frontmatter '{k}' 없음")
    if "desk" in fm and fm["desk"] not in DESKS:
        report.add("ERROR", path, at["desk"], "desk", f"desk 허용값 아님: {fm['desk']!r} (허용: {', '.join(sorted(DESKS))})")
    if "aiDrafted" in fm and fm["aiDrafted"] is not True:
        report.add("ERROR", path, at["aiDrafted"], "aiDrafted", f"aiDrafted가 true가 아님: {fm['aiDrafted']!r}")
    if "reviewedBy" in fm and fm["reviewedBy"] and fm["reviewedBy"] != REVIEWER:
        report.add("ERROR", path, at["reviewedBy"], "reviewedBy", f"reviewedBy가 '{REVIEWER}'가 아님: {fm['reviewedBy']!r}")
    if "date" in fm:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fm["date"])):
            report.add("ERROR", path, at["date"], "date", f"date 형식이 YYYY-MM-DD가 아님: {fm['date']!r}")
        elif post.date and fm["date"] != post.date:
            report.add("ERROR", path, at["date"], "date", f"date({fm['date']})와 파일명 날짜({post.date})가 다름")


def lint_text(post, report: Report) -> None:
    targets = [(post.fm_lines[k], str(post.frontmatter[k])) for k in ("title", "description") if k in post.frontmatter]
    targets += post.body
    for lineno, raw in targets:
        kc = mask(raw, keep_comments=True)
        scan = mask(raw)
        for code, rx, label in MONEY:
            for m in rx.finditer(scan):
                # 환율 수준값(…원<!--market.fx[0].rate_lvl-->)은 금액이 아니다
                c = COMMENT_RE.match(kc, m.end())
                if c and c.group(1).strip().endswith("_lvl"):
                    continue
                report.add("ERROR", post.path, lineno, code, f"{label} 노출 의심: '{m.group(0).strip()}'")
        for code, rx, label in ADVICE:
            for m in rx.finditer(scan):
                # 문맥 판단이 필요해 WARN. 최종 판단은 compliance가 한다.
                report.add("WARN", post.path, lineno, code, f"{label} 표현(문맥 확인): '{m.group(0).strip()}'")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--files-from")
    ap.add_argument("--content-root", default=str(CONTENT_ROOT))
    a = ap.parse_args(argv)
    paths = collect_paths(a.paths, a.files_from, Path(a.content_root))
    report = Report()
    for p in paths:
        post = load_post(p)
        lint_frontmatter(post, report)
        lint_text(post, report)
    return report.finish("content_lint", len(paths))


if __name__ == "__main__":
    sys.exit(main())
