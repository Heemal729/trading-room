"""검사 스크립트 자체 테스트. 가짜 글(fixtures/content)과 가짜 데이터(fixtures/data)만 쓴다.

실행: python -m unittest discover -s checks/tests -v
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import content_lint  # noqa: E402
import data_guard  # noqa: E402
import numbers_match  # noqa: E402

FIX = HERE / "fixtures"
DATA = FIX / "data" / "daily"
PASS_POST = FIX / "content" / "journal" / "2026-10-20-fixture-pass.md"
FAIL_POST = FIX / "content" / "journal" / "2026-10-20-fixture-FAIL.md"


def run(mod, *args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = mod.main(list(args))
    return code, out.getvalue()


def codes(output: str, level: str = "ERROR") -> list[str]:
    return re.findall(rf"{level} \[([A-Za-z-]+)]", output)


class NumbersMatchTest(unittest.TestCase):
    def test_pass_post(self):
        code, out = run(numbers_match, "--data-root", str(DATA), str(PASS_POST))
        self.assertEqual(code, 0, out)
        self.assertEqual(codes(out), [], out)

    def test_fail_post(self):
        code, out = run(numbers_match, "--data-root", str(DATA), str(FAIL_POST))
        self.assertEqual(code, 1, out)
        found = codes(out)
        self.assertIn("mismatch", found)  # -0.48 vs -0.84
        self.assertIn("key", found)  # [symbol=TSLA] 없음
        self.assertGreaterEqual(found.count("no-source"), 4)  # 18.3%, 120, 512.40, 1,240
        self.assertIn("sign", codes(out, "WARN"))  # 0.84 vs -0.84

    def test_missing_data_dir(self):
        code, out = run(numbers_match, "--data-root", str(FIX / "nowhere"), str(PASS_POST))
        self.assertEqual(code, 1, out)
        self.assertIn("meta", codes(out))


class ContentLintTest(unittest.TestCase):
    def test_pass_post(self):
        code, out = run(content_lint, "--data-root", str(DATA), str(PASS_POST))
        self.assertEqual(code, 0, out)

    def test_fail_post(self):
        code, out = run(content_lint, "--data-root", str(DATA), str(FAIL_POST))
        self.assertEqual(code, 1, out)
        errors = set(codes(out))
        expected_errors = {
            "filename", "frontmatter", "desk", "aiDrafted", "reviewedBy", "date",
            "money-usd", "money-krw", "shares",
        }
        self.assertEqual(expected_errors - errors, set(), out)
        # 권유·예측·보장 표현은 문맥 판단이 필요해 WARN이다
        self.assertEqual({"recommend", "forecast", "guarantee"} - set(codes(out, "WARN")), set(), out)
        self.assertEqual({"recommend", "forecast", "guarantee"} & errors, set(), out)

    def test_no_false_positive_on_common_phrases(self):
        ok = [
            "불확실성이 커졌다.",
            "수익률이 목표가 아니다.",
            "3주 연속 하락했다.",
            "원·달러 환율을 본다.",
            "통제 3원칙을 적용했다.",
        ]
        # 레포 안에 파일을 만들지 않는다. 컬렉션 폴더 이름 검사 때문에 journal/ 아래에 둔다.
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / "journal"
            tmp.mkdir()
            for i, line in enumerate(ok):
                post = tmp / f"2026-10-20-tmp-{i}.md"
                post.write_text(PASS_POST.read_text(encoding="utf-8") + "\n" + line + "\n", encoding="utf-8")
                code, out = run(content_lint, "--data-root", str(DATA), str(post))
                self.assertEqual(code, 0, f"{line!r}\n{out}")
                self.assertEqual(codes(out, "WARN"), [], f"{line!r}\n{out}")

    def _lint_tmp(self, collection: str, name: str, body: str, data_root: Path = DATA) -> tuple[int, str]:
        head = PASS_POST.read_text(encoding="utf-8").split("## 손익 요약")[0]
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / collection
            tmp.mkdir()
            post = tmp / name
            post.write_text(head.replace("2026-10-20", name[:10]) + body + "\n", encoding="utf-8")
            return run(content_lint, "--data-root", str(data_root), str(post))

    def test_pre_public_numbers_error(self):
        # 2026-10-21 가짜 데이터는 pre_public이다
        code, out = self._lint_tmp("journal", "2026-10-21-tmp-pre.md", "오늘은 1.11%<!--pnl.day.total_pct--> 올랐다.")
        self.assertEqual(code, 1, out)
        self.assertIn("pre-public", codes(out), out)

    def test_pre_public_buildlog_without_numbers_ok(self):
        code, out = self._lint_tmp("buildlog", "2026-10-21-tmp-build.md", "수익률과 비중은 공개 기준일 이후에 쓴다.")
        self.assertEqual(code, 0, out)
        self.assertEqual(codes(out, "WARN"), [], out)

    def test_pre_public_words_warn(self):
        code, out = self._lint_tmp("buildlog", "2026-10-21-tmp-words.md", "비중 한도는 20%<!--memo-->로 정했다.")
        self.assertEqual(code, 0, out)
        self.assertIn("pre-public-words", codes(out, "WARN"), out)

    def test_no_meta_means_pre_public(self):
        code, out = self._lint_tmp("journal", "2026-10-20-tmp-nometa.md", "오늘은 -0.84%<!--pnl.day.total_pct--> 손실이다.", FIX / "nowhere")
        self.assertEqual(code, 1, out)
        self.assertIn("pre-public", codes(out), out)


class DataGuardTest(unittest.TestCase):
    """PR이 공개 전 데이터를 추가·변경하면 실패해야 한다."""

    def test_pre_public_data_fails(self):
        code, out = run(data_guard, "--data-root", str(DATA), "data/daily/2026-10-21/pnl.json", "data/daily/2026-10-21/meta.json")
        self.assertEqual(code, 1, out)
        self.assertEqual(codes(out), ["pre-public"], out)  # 날짜당 한 번

    def test_public_data_passes(self):
        code, out = run(data_guard, "--data-root", str(DATA), "data/daily/2026-10-20/pnl.json")
        self.assertEqual(code, 0, out)

    def test_non_data_files_ignored(self):
        code, out = run(data_guard, "--data-root", str(DATA), "blog/src/content/buildlog/2026-10-21-x.md", "data/README.md")
        self.assertEqual(code, 0, out)

    def test_files_from_list(self):
        with tempfile.TemporaryDirectory() as d:
            lst = Path(d) / "changed.txt"
            lst.write_text("data/daily/2026-10-20/meta.json\ndata/daily/2026-10-21/pnl.json\n", encoding="utf-8")
            code, out = run(data_guard, "--data-root", str(DATA), "--files-from", str(lst))
        self.assertEqual(code, 1, out)
        self.assertEqual(codes(out), ["pre-public"], out)

    def test_edge_cases(self):
        cases = {
            "missing-field": ({"date": "2026-10-23", "stale": False, "notes": []}, "pre-public"),
            "before-inception": ({"date": "2026-10-23", "public_inception": "2026-11-02", "notes": []}, "pre-public"),
            "bad-format": ({"date": "2026-10-23", "public_inception": "11/02", "notes": []}, "pre-public"),
            "no-meta": (None, "meta"),
        }
        for label, (meta, expected) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                day = Path(d) / "2026-10-23"
                day.mkdir()
                if meta is not None:
                    (day / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
                code, out = run(data_guard, "--data-root", d, "data/daily/2026-10-23/positions.json")
                self.assertEqual(code, 1, out)
                self.assertEqual(codes(out), [expected], out)

    def test_outside_date_folder_fails(self):
        code, out = run(data_guard, "--data-root", str(DATA), "data/daily/notes.json")
        self.assertEqual(code, 1, out)
        self.assertEqual(codes(out), ["data-path"], out)


if __name__ == "__main__":
    unittest.main()
