import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getCollection } from 'astro:content';
import { SECTIONS, SITE_DESCRIPTION, SITE_TITLE } from '../consts';
import { withBase } from '../lib/path';

export async function GET(context: APIContext) {
	const grouped = await Promise.all(
		SECTIONS.map(async (section) => {
			const posts = await getCollection(section.id);
			return posts.map((post) => ({
				title: post.data.title,
				description: post.data.description ?? '',
				pubDate: post.data.date,
				categories: [section.label, post.data.desk],
				link: withBase(`/${section.id}/${post.id}/`),
			}));
		}),
	);

	const items = grouped.flat().sort((a, b) => b.pubDate.valueOf() - a.pubDate.valueOf());

	return rss({
		title: SITE_TITLE,
		description: SITE_DESCRIPTION,
		site: new URL(withBase('/'), context.site ?? 'https://heemal729.github.io'),
		items,
	});
}
