---
title: '레포 골격 세팅'
date: 2026-10-21
desk: 'Infra'
aiDrafted: false
reviewedBy: 'Heemal729'
description: 'Astro 블로그 + GitHub Pages + 시크릿 스캔까지 한 번에.'
---

## 한 일

- `blog/`에 Astro 블로그(TypeScript strict)
- 콘텐츠 컬렉션 3개: `journal`, `market`, `buildlog`
- GitHub Actions로 Pages 배포
- pre-commit + gitleaks로 커밋 전 시크릿 스캔

## 다음

데스크 산출물(`desks/outputs/`)과 일일 데이터(`data/daily/`)를 어떤 포맷으로 커밋할지 정한다.
