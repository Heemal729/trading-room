"""checks/ 스크립트가 함께 쓰는 글 읽기·보고 도구. 표준 라이브러리만 쓴다."""
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTENT_ROOT = REPO_ROOT / "blog" / "src" / "content"
DATA_ROOT = REPO_ROOT / "data" / "daily"

COMMENT_RE = re.compile(r"<!--(.*?)-->")
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def pre_public_reason(meta: dict, date: str | None = None) -> str | None:
    """공개 전 데이터면 그 이유를, 공개해도 되는 데이터면 None을 돌려준다 (CLAUDE.md 절대 규칙 9).

    필드가 없는 옛 export도 공개 전으로 본다. date를 주지 않으면 meta의 date와 비교한다.
    """
    if "public_inception" not in meta:
        return "meta.json에 public_inception 필드 없음"
    inception = meta["public_inception"]
    if inception is None:
        return "public_inception이 null"
    if "pre_public" in (meta.get("notes") or []):
        return "notes에 pre_public"
    if not isinstance(inception, str) or not DATE_ONLY_RE.match(inception):
        return f"public_inception 형식이 YYYY-MM-DD가 아님: {inception!r}"
    d = date or meta.get("date")
    if isinstance(d, str) and d < inception:
        return f"날짜 {d}가 public_inception {inception} 이전"
    return None


def load_meta(path: Path) -> tuple[dict | None, str | None]:
    """meta.json을 읽는다. (내용, 오류 메시지)"""
    if not path.exists():
        return None, f"{path.as_posix()} 없음"
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"{path.name} JSON 파싱 실패: {e}"
    if not isinstance(meta, dict):
        return None, f"{path.name}이 객체가 아님"
    return meta, None


@dataclass
class Post:
    path: Path
    frontmatter: dict[str, str | bool]
    fm_lines: dict[str, int]  # 키 → 파일 줄 번호
    body: list[tuple[int, str]]  # (파일 줄 번호, 원문). 코드 블록은 빠져 있다.
    has_frontmatter: bool

    @property
    def date(self) -> str | None:
        # 슬러그가 규칙에 어긋나도 날짜는 읽는다. 슬러그 검사는 content_lint가 한다.
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-", self.path.name)
        return m.group(1) if m else None


def _scalar(raw: str) -> str | bool:
    v = raw.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    if v == "true":
        return True
    if v == "false":
        return False
    # 따옴표 없는 값 뒤의 주석 제거
    return re.sub(r"\s+#.*$", "", v)


def load_post(path: Path) -> Post:
    lines = path.read_text(encoding="utf-8").splitlines()
    fm: dict[str, str | bool] = {}
    fm_lines: dict[str, int] = {}
    start = 0
    has_fm = False
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                has_fm = True
                start = i + 1
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", lines[i])
            if m:
                fm[m.group(1)] = _scalar(m.group(2))
                fm_lines[m.group(1)] = i + 1
        if not has_fm:
            fm, fm_lines = {}, {}

    body: list[tuple[int, str]] = []
    in_fence = False
    for i in range(start, len(lines)):
        line = lines[i]
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            body.append((i + 1, line))
    return Post(path, fm, fm_lines, body, has_fm)


def mask(line: str, keep_comments: bool = False) -> str:
    """인라인 코드, 링크 주소, (선택) HTML 주석을 같은 길이의 공백으로 가린다. 위치는 유지된다."""
    blank = lambda m: " " * len(m.group(0))
    line = re.sub(r"`[^`]*`", blank, line)
    line = re.sub(r"\]\([^)]*\)", lambda m: "]" + " " * (len(m.group(0)) - 1), line)
    if not keep_comments:
        line = COMMENT_RE.sub(blank, line)
    return line


def collect_paths(args_paths: list[str], files_from: str | None, content_root: Path) -> list[Path]:
    paths: list[str] = list(args_paths)
    if files_from:
        with open(files_from, encoding="utf-8") as f:
            paths += [p.strip() for p in f if p.strip()]
        return [Path(p) for p in paths if p.endswith(".md")]
    if paths:
        return [Path(p) for p in paths]
    return sorted(p for p in content_root.rglob("*.md"))


@dataclass
class Report:
    errors: int = 0
    warnings: int = 0
    lines: list[str] = field(default_factory=list)

    def add(self, level: str, path: Path, line: int, code: str, msg: str) -> None:
        if level == "ERROR":
            self.errors += 1
        else:
            self.warnings += 1
        rel = _rel(path)
        self.lines.append(f"{rel}:{line}: {level} [{code}] {msg}")
        if os.environ.get("GITHUB_ACTIONS") == "true":
            kind = "error" if level == "ERROR" else "warning"
            print(f"::{kind} file={rel},line={line}::[{code}] {msg}")

    def finish(self, name: str, n_files: int, unit: str = "글") -> int:
        for line in self.lines:
            print(line)
        print(f"{name}: {unit} {n_files}개, 오류 {self.errors}, 경고 {self.warnings}")
        return 1 if self.errors else 0


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def utf8_stdout() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
