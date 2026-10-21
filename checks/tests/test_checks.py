"""검사 스크립트 자체 테스트. 가짜 글(fixtures/content)과 가짜 데이터(fixtures/data)만 쓴다.

실행: python -m unittest discover -s checks/tests -v
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import content_lint  # noqa: E402
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
        code, out = run(content_lint, str(PASS_POST))
        self.assertEqual(code, 0, out)

    def test_fail_post(self):
        code, out = run(content_lint, str(FAIL_POST))
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
                code, out = run(content_lint, str(post))
                self.assertEqual(code, 0, f"{line!r}\n{out}")
                self.assertEqual(codes(out, "WARN"), [], f"{line!r}\n{out}")


if __name__ == "__main__":
    unittest.main()
