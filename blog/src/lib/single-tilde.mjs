// Satteri mdast plugin: keep single-tilde strikethrough as literal text.
//
// GFM parses `~text~` as strikethrough, so Korean range notation such as
// "15~20% and 30~40%" on one line renders as <del>. Satteri has no
// `singleTilde: false` option (remark-gfm had one), so this plugin restores
// the tildes when a `delete` node was opened with a single `~`.
// Double-tilde strikethrough (`~~text~~`) is kept.
export const singleTildeLiteral = {
	name: 'single-tilde-literal',
	options: { position: true },
	delete(node, ctx) {
		const start = node.position?.start?.offset;
		if (start == null || ctx.source.startsWith('~~', start)) return;
		ctx.replaceNode(node, [{ type: 'text', value: '~' }, ...node.children, { type: 'text', value: '~' }]);
	},
};
