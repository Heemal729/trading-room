/**
 * `base`(= '/trading-room')가 붙은 사이트에서 내부 링크를 만들 때 쓴다.
 * Astro는 하드코딩된 href에 base를 자동으로 붙여주지 않는다.
 */
const BASE = import.meta.env.BASE_URL.replace(/\/+$/, '');

export function withBase(path = '/'): string {
	const clean = `/${path}`.replace(/\/{2,}/g, '/');
	return clean === '/' ? `${BASE}/` : `${BASE}${clean}`;
}

/** 현재 URL에서 base를 떼낸 경로. 활성 링크 판별에 쓴다. */
export function stripBase(pathname: string): string {
	const stripped = pathname.startsWith(BASE) ? pathname.slice(BASE.length) : pathname;
	return stripped === '' ? '/' : stripped;
}
