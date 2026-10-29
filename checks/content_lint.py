"""글의 금액·수량 노출, 권유·예측 표현, frontmatter, 공개 전 운용 숫자를 검사한다
(CLAUDE.md 절대 규칙 3·4·9, frontmatter 절, compliance 검사 항목 2·3·6·10).

금액·수량·frontmatter는 ERROR, 권유·예측·보장 표현은 WARN이다.
한 줄에 단일 물결표(~)가 두 개 이상이면 WARN이다. 블로그 설정이 단일 물결표 취소선을 끄지만,
설정이 빠지거나 바뀌면 "15~20%와 30~40%"가 취소선으로 렌더링되므로 백업으로 본다.
정규식 검사라 문맥을 읽지 못하므로 WARN 표현은 compliance가 문맥으로 최종 판단한다.
금액·수량 패턴이 의도보다 넓다면 이 파일의 패턴을 PR로 고친다.

공개 전(글 날짜가 public_inception 전) 글:
- 계좌 데이터 출처 주석(<!--pnl.…-->, positions, trades, risk)이 붙은 숫자는 ERROR다.
- 수익률·손익·비중·기여라는 말과 %·%p·bp 숫자가 한 줄에 있으면 WARN이다(규칙 설명일 수 있어 compliance가 판단).
- 공개 여부는 data/daily/<글 날짜>/meta.json으로, 그 폴더가 없으면 가장 최근 meta.json으로 판단한다.
  meta.json이 하나도 없으면 공개 전으로 본다. 구축기는 운용 숫자 없이 쓰면 된다.

사용법: python checks/content_lint.py [글.md ...] [--files-from 목록.txt] [--data-root DIR]
글을 지정하지 않으면 blog/src/content 아래 글 전부를 본다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from postlib import (
    COMMENT_RE,
    CONTENT_ROOT,
    DATA_ROOT,
    FILENAME_RE,
    Report,
    collect_paths,
    load_meta,
    load_post,
    mask,
    pre_public_reason,
    utf8_stdout,
)

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
# ~~취소~~(두 개짜리)와 \~(이스케이프)는 세지 않는다
SINGLE_TILDE = re.compile(r"(?<![~\\])~(?!~)")
# 계좌 운용 숫자의 출처 파일. market.json(시장 지표)은 공개 전에도 쓸 수 있다.
ACCOUNT_KEY_RE = re.compile(r"^\s*(?:pnl|positions|trades|risk)[.\[]")
ACCOUNT_WORD_RE = re.compile(r"수익률|손익|비중|기여")
PCT_NUM_RE = re.compile(rf"{NUM}\s?(?:%p|%|bps|bp)")


def pre_public_for_post(date: str | None, data_root: Path) -> str | None:
    """글 날짜가 공개 전이면 이유를, 공개 후면 None을 돌려준다."""
    if date is None:
        return "글 날짜를 읽지 못함"
    meta_path = data_root / date / "meta.json"
    if not meta_path.exists():
        metas = sorted(data_root.glob("*/meta.json")) if data_root.is_dir() else []
        if not metas:
            return f"{data_root.as_posix()}에 meta.json이 없어 공개 기준일을 확인할 수 없음"
        meta_path = metas[-1]  # 폴더 이름이 날짜라 정렬하면 마지막이 최신
    meta, err = load_meta(meta_path)
    if err:
        return err
    return pre_public_reason(meta, date)


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


def lint_pre_public(post, data_root: Path, report: Report) -> None:
    reason = pre_public_for_post(post.date, data_root)
    if reason is None:
        return
    targets = [(post.fm_lines[k], str(post.frontmatter[k])) for k in ("title", "description") if k in post.frontmatter]
    targets += post.body
    for lineno, raw in targets:
        keys = [c.group(1).strip() for c in COMMENT_RE.finditer(mask(raw, keep_comments=True))]
        account = [k for k in keys if ACCOUNT_KEY_RE.match(k)]
        if account:
            report.add("ERROR", post.path, lineno, "pre-public", f"공개 전 글에 운용 숫자({', '.join(account)}): {reason}")
            continue
        scan = mask(raw)
        if ACCOUNT_WORD_RE.search(scan) and PCT_NUM_RE.search(scan):
            report.add("WARN", post.path, lineno, "pre-public-words", f"공개 전 글에 수익률·손익·비중 숫자로 보이는 표현(문맥 확인): {reason}")


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
        if len(SINGLE_TILDE.findall(scan)) >= 2:
            report.add("WARN", post.path, lineno, "single-tilde", "한 줄에 단일 물결표가 두 개 이상: 설정이 빠지면 취소선으로 렌더링됨(렌더링 확인)")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--files-from")
    ap.add_argument("--content-root", default=str(CONTENT_ROOT))
    ap.add_argument("--data-root", default=str(DATA_ROOT))
    a = ap.parse_args(argv)
    paths = collect_paths(a.paths, a.files_from, Path(a.content_root))
    report = Report()
    for p in paths:
        post = load_post(p)
        lint_frontmatter(post, report)
        lint_text(post, report)
        lint_pre_public(post, Path(a.data_root), report)
    return report.finish("content_lint", len(paths))


if __name__ == "__main__":
    sys.exit(main())
