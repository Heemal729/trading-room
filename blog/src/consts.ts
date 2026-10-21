// Place any global data in this file.
// You can import this data from anywhere in your site by using the `import` keyword.

export const SITE_TITLE = 'AI 트레이딩룸';
export const SITE_DESCRIPTION = 'AI와 함께 운영하는 트레이딩룸 — 매매일지, 시황, 구축기.';

/** 글 컬렉션(= 섹션) 정의. 네비게이션과 목록 페이지가 이 값을 공유한다. */
export const SECTIONS = [
	{ id: 'journal', label: '매매일지', description: '하루 단위 체결·판단·회고 기록.' },
	{ id: 'market', label: '시황', description: '시장 데이터 기반 관측과 해석.' },
	{ id: 'buildlog', label: '구축기', description: '트레이딩룸 자체를 만들어가는 과정.' },
] as const;

export type SectionId = (typeof SECTIONS)[number]['id'];

export const SECTION_LABEL: Record<SectionId, string> = {
	journal: '매매일지',
	market: '시황',
	buildlog: '구축기',
};

/** aiDrafted === true 인 글 하단에 붙는 고정 표기. */
export const AI_DRAFT_NOTICE = 'AI 초안 · 본인 검수';
