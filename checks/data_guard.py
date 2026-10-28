"""PR이 추가·변경하는 data/daily/ 파일이 공개 전 데이터인지 검사한다 (CLAUDE.md 절대 규칙 9).

- 바뀐 파일마다 같은 날짜 폴더의 meta.json을 읽는다.
- 다음이면 오류다: meta.json 없음·파싱 실패, public_inception 필드 없음·null,
  notes에 pre_public, 날짜가 public_inception 이전, 날짜 폴더 밖의 파일.
- 삭제된 파일은 검사하지 않는다(목록에 넣지 않는다).

사용법: python checks/data_guard.py [파일 ...] [--files-from 목록.txt] [--data-root DIR]
파일 경로는 레포 기준(data/daily/YYYY-MM-DD/<파일>)으로 준다. 날짜 폴더는 --data-root 아래에서 찾는다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from postlib import DATA_ROOT, Report, load_meta, pre_public_reason, utf8_stdout

DAILY_RE = re.compile(r"(?:^|/)data/daily/(?:(\d{4}-\d{2}-\d{2})/)?")


def check(paths: list[str], data_root: Path, report: Report) -> int:
    by_date: dict[str, list[str]] = {}
    n = 0
    for p in paths:
        posix = p.replace("\\", "/")
        m = DAILY_RE.search(posix)
        if not m:
            continue
        n += 1
        if m.group(1) is None:
            report.add("ERROR", Path(p), 1, "data-path", "data/daily/ 아래 날짜 폴더(YYYY-MM-DD) 밖의 파일")
            continue
        by_date.setdefault(m.group(1), []).append(posix)
    for date, files in sorted(by_date.items()):
        meta_path = data_root / date / "meta.json"
        meta, err = load_meta(meta_path)
        listed = ", ".join(Path(f).name for f in files)
        if err:
            report.add("ERROR", meta_path, 1, "meta", f"{err}. 공개 여부를 확인할 수 없음 ({listed})")
            continue
        reason = pre_public_reason(meta, date)
        if reason:
            report.add("ERROR", meta_path, 1, "pre-public", f"공개 전 데이터라 커밋할 수 없음: {reason} ({listed})")
    return n


def main(argv: list[str] | None = None) -> int:
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--files-from")
    ap.add_argument("--data-root", default=str(DATA_ROOT))
    a = ap.parse_args(argv)
    paths = list(a.paths)
    if a.files_from:
        with open(a.files_from, encoding="utf-8") as f:
            paths += [line.strip() for line in f if line.strip()]
    report = Report()
    n = check(paths, Path(a.data_root), report)
    return report.finish("data_guard", n, unit="데이터 파일")


if __name__ == "__main__":
    sys.exit(main())
