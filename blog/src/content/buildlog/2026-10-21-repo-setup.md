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

## 어떻게 고쳤나

- 스키마 인자를 `SchemaContext`로 바꿨다. deprecated된 `z.ZodIssueCode.custom`도 문자열 `'custom'`으로 교체했다.
- `.pre-commit-config.yaml`의 주석을 영문으로 바꿨다. 설정 파일만 ASCII로 두면 한글 콘텐츠 파일은 정상적으로 스캔된다.
- Pages 소스 설정은 레포 설정에서 수동으로 바꿔야 한다. 코드로 해결할 문제가 아니었다.

## 남은 것

- `aiDrafted: true`를 스키마에서 강제할지 결정해야 한다. 지금은 기본값이 `false`라 규칙 위반이 조용히 통과한다.
- 데스크 산출물(`desks/outputs/`)과 일일 데이터(`data/daily/`)의 JSON 포맷이 아직 없다.
- `checks/restricted.txt`를 실제로 검사하는 스크립트가 없다. 목록만 있고 게이트가 없는 상태다.
