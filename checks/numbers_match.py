"""글 속 숫자와 출처 주석을 검사한다 (CLAUDE.md 절대 규칙 2, compliance 검사 항목 1).

- 숫자 바로 뒤의 <!--키경로--> 값을 data/daily/<글 날짜>/ JSON에서 찾아,
  글에 쓴 자릿수로 반올림한 값과 같은지 본다.
- 출처 주석이 없는 숫자는 오류다. <!--memo--> 숫자는 대조하지 않고 경고로 목록만 남긴다.
- 검사 대상이 아닌 숫자: 날짜·시각, 글 번호(#0), 버전(v1.2), 섹션·목록 번호,
  개수·순서 표현(세 가지, 3개, 2단계), 용어에 들어간 숫자(4-eyes, US10Y, S&P 500).

키경로 문법: <파일>.<키>... 배열은 [0] 또는 [symbol=SPX]
  예) pnl.day.total_pct, market.indices[0].chg_pct, pnl.contrib[symbol=SOXL].contrib_bp

사용법: python checks/numbers_match.py [글.md ...] [--files-from 목록.txt] [--data-root DIR]
글을 지정하지 않으면 blog/src/content 아래 글 전부를 본다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

from postlib import COMMENT_RE, CONTENT_ROOT, DATA_ROOT, Report, collect_paths, load_post, mask, utf8_stdout

NUMBER_RE = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\d,]*\d)")
DATE_RE = re.compile(
    r"\d{4}-\d{1,2}-\d{1,2}|\d{4}\.\d{1,2}\.\d{1,2}|\d{4}/\d{1,2}(?:/\d{1,2})?|\d{1,2}:\d{2}(?::\d{2})?"
)
# 지수 이름처럼 이름 자체에 숫자가 들어간 용어
NAMED_RE = re.compile(
    r"(?:S&P|Nasdaq|NASDAQ|나스닥|Russell|러셀|KOSPI|코스피|KOSDAQ|코스닥|Dow|다우|"
    r"STOXX|Stoxx|Nikkei|니케이|FTSE|DAX|CAC)\s?\d+"
)
# 날짜 단위, 개수·순서 표현
COUNT_SUFFIX_RE = re.compile(
    r"^\s?(?:주년|분기|번째|가지|단계|종목|년|월|일|시|분|초|개|차|회|건|명|곳|장|절|줄|번|위|호)"
)
UNIT_RE = re.compile(r"^(?:%p|%|bps|bp|pt|p|x|배|원)?")  # 원: 환율 수준값(1,385.2원)
KEY_RE = re.compile(r"^[a-z_]+(?:\.[A-Za-z_][A-Za-z0-9_]*|\.\d+|\[\d+\]|\[[A-Za-z_]+=[^\]]+\])+$")
STEP_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\.(\d+)|\[(\d+)\]|\[([A-Za-z_]+)=([^\]]+)\]")

_MISSING = object()


def resolve(data_dir: Path, key: str, cache: dict[Path, object]) -> tuple[object, str | None]:
    """키경로의 값을 찾는다. (값, 오류 메시지)"""
    head, rest = re.match(r"^([a-z_]+)(.*)$", key).groups()
    path = data_dir / f"{head}.json"
    if path not in cache:
        if not path.exists():
            cache[path] = _MISSING
        else:
            try:
                cache[path] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                return None, f"{path.name} JSON 파싱 실패: {e}"
    node = cache[path]
    if node is _MISSING:
        return None, f"{path.as_posix()} 없음"
    for m in STEP_RE.finditer(rest):
        name, dot_idx, br_idx, sel_k, sel_v = m.groups()
        if name is not None:
            if not isinstance(node, dict) or name not in node:
                return None, f"키 '{name}' 없음"
            node = node[name]
        elif dot_idx is not None or br_idx is not None:
            i = int(dot_idx if dot_idx is not None else br_idx)
            if not isinstance(node, list) or i >= len(node):
                return None, f"배열 인덱스 {i} 없음"
            node = node[i]
        else:
            if not isinstance(node, list):
                return None, f"[{sel_k}={sel_v}]를 쓸 수 있는 배열이 아님"
            found = [x for x in node if isinstance(x, dict) and str(x.get(sel_k)) == sel_v]
            if not found:
                return None, f"[{sel_k}={sel_v}]에 맞는 항목 없음"
            node = found[0]
    return node, None


def compare(text_num: str, sign: str, value: object) -> tuple[str, str] | None:
    """일치하면 None. 아니면 (등급, 메시지)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "ERROR", f"JSON 값이 숫자가 아님: {json.dumps(value, ensure_ascii=False)}"
    digits = text_num.replace(",", "")
    places = len(digits.split(".", 1)[1]) if "." in digits else 0
    try:
        written = Decimal(digits)
    except InvalidOperation:
        return "ERROR", f"숫자 해석 실패: {text_num}"
    rounded = Decimal(repr(value)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    if sign in ("-", "−"):
        written = -written
    if written == rounded:
        return None
    if not sign and rounded < 0 and written == -rounded:
        return "WARN", f"부호 생략: 글 {text_num}, JSON {value}"
    return "ERROR", f"값 불일치: 글 {sign}{text_num}, JSON {value} (소수 {places}자리 반올림 {rounded})"


def check_post(path: Path, data_root: Path, report: Report) -> None:
    post = load_post(path)
    date = post.date
    data_dir = data_root / date if date else None
    cache: dict[Path, object] = {}
    meta_checked = False

    for lineno, raw in post.body:
        kc = mask(raw, keep_comments=True)
        scan = mask(raw)
        comments = {m.start(): m.group(1).strip() for m in COMMENT_RE.finditer(kc)}
        used: set[int] = set()
        skip_spans = [m.span() for m in DATE_RE.finditer(scan)] + [m.span() for m in NAMED_RE.finditer(scan)]

        for m in NUMBER_RE.finditer(scan):
            s, e = m.span()
            num = m.group(1)
            if any(a <= s < b for a, b in skip_spans):
                continue
            # 부호: 앞 글자가 +/-이고 그 앞이 문자·숫자가 아니면 부호로 본다
            sign = ""
            lead = s
            if s > 0 and scan[s - 1] in "+-−" and (s == 1 or not scan[s - 2].isalnum()):
                sign = scan[s - 1]
                lead = s - 1
            before = scan[lead - 1] if lead > 0 else ""
            after = scan[e:]
            if before == "#":
                continue  # 글 번호 #0
            if before and (before.isascii() and before.isalpha() or before in "&_+"):
                continue  # US10Y, v1.2, T+1
            if re.match(r"^-[A-Za-z가-힣]", after):
                continue  # 4-eyes
            if COUNT_SUFFIX_RE.match(after):
                continue  # 세 가지, 3개, 1단계, 2020년
            if not scan[:lead].strip() and re.match(r"^[.)]\s", after):
                continue  # 목록 번호 1.
            if raw.lstrip().startswith("#") and not re.sub(r"^\s*#+", "", scan[:lead]).strip():
                continue  # 제목의 섹션 번호

            unit = UNIT_RE.match(after).group(0)
            c_pos = e + len(unit)
            shown = f"{sign}{num}{unit}"
            if c_pos not in comments:
                report.add("ERROR", path, lineno, "no-source", f"출처 주석 없는 숫자: {shown}")
                continue
            used.add(c_pos)
            key = comments[c_pos]
            if key == "memo":
                report.add("WARN", path, lineno, "memo", f"운영자 메모 숫자(대조 안 함): {shown}")
                continue
            if not KEY_RE.match(key):
                report.add("ERROR", path, lineno, "bad-key", f"출처 주석 형식이 아님: <!--{key}-->")
                continue
            if data_dir is None:
                report.add("ERROR", path, lineno, "no-date", "파일명에서 날짜를 읽을 수 없어 데이터 폴더를 찾지 못함")
                continue
            if not meta_checked:
                meta_checked = True
                meta, err = resolve(data_dir, "meta.stale", cache)
                if err:
                    report.add("ERROR", path, lineno, "meta", f"meta.json 확인 실패({err}). 규칙 7: 데이터 없음")
                elif meta is not False:
                    report.add("ERROR", path, lineno, "stale", f"meta.json stale={meta}. 규칙 7: 데이터가 오래됨")
            value, err = resolve(data_dir, key, cache)
            if err:
                report.add("ERROR", path, lineno, "key", f"<!--{key}-->: {err}")
                continue
            result = compare(num, sign, value)
            if result:
                level, msg = result
                report.add(level, path, lineno, "mismatch" if level == "ERROR" else "sign", f"<!--{key}-->: {msg}")

        for pos, key in comments.items():
            if pos not in used and (key == "memo" or KEY_RE.match(key)):
                report.add("WARN", path, lineno, "dangling", f"앞에 숫자가 없는 출처 주석: <!--{key}-->")


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--files-from")
    ap.add_argument("--data-root", default=str(DATA_ROOT))
    ap.add_argument("--content-root", default=str(CONTENT_ROOT))
    a = ap.parse_args(argv)
    paths = collect_paths(a.paths, a.files_from, Path(a.content_root))
    report = Report()
    for p in paths:
        check_post(p, Path(a.data_root), report)
    return report.finish("numbers_match", len(paths))


if __name__ == "__main__":
    sys.exit(main())
