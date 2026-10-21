---
title: '레포 골격 세팅'
date: 2026-10-21
desk: 'Infra'
aiDrafted: true
reviewedBy: '구동섭'
description: 'Astro 블로그 + GitHub Pages + 시크릿 스캔까지 한 번에.'
---

## 무엇을 만들었나

- `blog/`에 Astro 블로그. TypeScript strict, `base`는 `/trading-room`.
- 콘텐츠 컬렉션 3개: `journal`, `market`, `buildlog`. frontmatter 스키마를 공유한다.
- GitHub Actions로 `blog/`를 빌드해 Pages에 배포.
- pre-commit + gitleaks로 커밋 전 시크릿 스캔.
- 골격 디렉터리: `.claude/agents/`, `data/daily/`, `desks/outputs/`, `checks/`.

## 무엇이 틀렸나

- 컬렉션 스키마 팩토리의 인자 타입을 직접 적었더니 `astro check`가 거부했다. Astro가 넘기는 것은 `SchemaContext`다.
- `pre-commit autoupdate`가 `UnicodeDecodeError: cp949`로 죽었다. 설정 파일에 한글 주석을 넣은 것이 원인이었다.
- 첫 배포가 404로 실패했다. 워크플로 문제가 아니라 Pages 소스가 `GitHub Actions`로 설정되지 않은 상태였다.
- 제한종목 장치를 먼저 만들었다. 정작 매매 대상은 미국 상장 주식·ETF뿐이어서 제한종목 목록이 필요한 구조가 아니었다. 공개 레포에 목록을 두면 "무엇이 제한종목인지"가 그대로 드러나 제한 사유가 역추적된다는 문제도 있었다.

## 어떻게 고쳤나

- 스키마 인자를 `SchemaContext`로 바꿨다. deprecated된 `z.ZodIssueCode.custom`도 문자열 `'custom'`으로 교체했다.
- `.pre-commit-config.yaml`의 주석을 영문으로 바꿨다. 설정 파일만 ASCII로 두면 한글 콘텐츠 파일은 정상적으로 스캔된다.
- Pages 소스 설정은 레포 설정에서 수동으로 바꿔야 한다. 코드로 해결할 문제가 아니었다.
- 미국 주식만 매매하기로 정리하면서 제한종목 장치를 걷어냈다. `checks/restricted.txt`를 삭제하고, 국내 개별 종목을 글에서 다루지 않는다는 규칙으로 대체했다. 지수나 환율처럼 시장 전체 수준의 언급은 남겨뒀다.

## 남은 것

- `aiDrafted: true`를 스키마에서 강제할지 결정해야 한다. 지금은 기본값이 `false`라 규칙 위반이 조용히 통과한다.
- 일일 데이터의 JSON 포맷은 `data/README.md`에 v0 초안으로 적었다. 실제 파일과 데스크 산출물(`desks/outputs/`) 포맷은 아직 없다.
- 규칙을 검사하는 스크립트가 `checks/`에 없다. 숫자 출처 주석과 금액·수량 비공개는 아직 사람 눈에만 의존한다.
