import { defineCollection, type SchemaContext } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

/**
 * 세 컬렉션이 공유하는 frontmatter 스키마.
 * aiDrafted가 true인 글은 reviewedBy가 반드시 채워져 있어야 빌드가 통과한다.
 */
const postSchema = ({ image }: SchemaContext) =>
	z
		.object({
			title: z.string().min(1),
			// 문자열(2026-10-21)을 Date로 변환
			date: z.coerce.date(),
			// 어느 데스크에서 나온 글인지
			desk: z.string().min(1),
			// AI가 초안을 썼는지
			aiDrafted: z.boolean().default(false),
			// 검수한 사람
			reviewedBy: z.string().min(1).optional(),
			description: z.string().optional(),
			heroImage: z.optional(image()),
		})
		.superRefine((data, ctx) => {
			if (data.aiDrafted && !data.reviewedBy) {
				ctx.addIssue({
					code: 'custom',
					path: ['reviewedBy'],
					message: 'aiDrafted: true 인 글은 reviewedBy(검수자)를 반드시 적어야 합니다.',
				});
			}
		});

const collection = (dir: string) =>
	defineCollection({
		loader: glob({ base: `./src/content/${dir}`, pattern: '**/*.{md,mdx}' }),
		schema: postSchema,
	});

const journal = collection('journal');
const market = collection('market');
const buildlog = collection('buildlog');

export const collections = { journal, market, buildlog };
