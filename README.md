# AI 트레이딩룸

매매 판단과 그 근거를 공개로 기록하는 트레이딩룸. 글 일부는 AI가 초안을 쓰고 사람이 검수합니다.

공개 사이트: https://heemal729.github.io/trading-room

## 구조

```
blog/              Astro 블로그 (TypeScript strict) — GitHub Pages로 배포
  src/content/
    journal/       매매일지
    market/        시황
    buildlog/      구축기
.claude/agents/    데스크별 에이전트 정의
data/daily/        일일 가공 데이터 (커밋)
data/raw/          원천 데이터 (gitignore)
desks/outputs/     데스크 산출물
checks/            검증 스크립트
```

## 글 frontmatter

```yaml
---
title: '제목'
date: 2026-10-21
desk: 'KOSPI'
aiDrafted: true       # AI가 초안을 썼는가
reviewedBy: 'Heemal729'
description: '선택'
---
```

`aiDrafted: true`면 글 하단에 **AI 초안 · 본인 검수** 표기가 자동으로 붙습니다.
이때 `reviewedBy`가 비어 있으면 빌드가 실패합니다 (`blog/src/content.config.ts`).

## 로컬 실행

```bash
cd blog
npm install
npm run dev      # http://localhost:4321/trading-room
npm run build
npx astro check  # 타입 + 스키마 검증
```

## 시크릿 스캔

```bash
pip install pre-commit
pre-commit install          # 커밋마다 gitleaks 실행
pre-commit run --all-files  # 전체 스캔
```

## 면책

이 레포의 모든 내용은 기록·학습 목적이며 투자 권유가 아닙니다.
