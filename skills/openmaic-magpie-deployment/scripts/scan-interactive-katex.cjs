#!/usr/bin/env node
/**
 * Dump every stored interactive page and report its KaTeX situation.
 *
 * Run from the repo root:
 *   set -a && . ./.env.local && set +a && node <this-file> [outDir]
 *
 * Why this exists: whether an interactive page "needs KaTeX" cannot be
 * answered by counting `$` in the raw HTML — in real stored pages every `$`
 * is JavaScript (`$('canvas')`, `${phase()}`). This probe separates the
 * delimiters that live in the rendered body from the ones that live inside
 * `<script>` bodies, and flags the pages that still carry a CDN KaTeX block.
 *
 * No psql binary is available in this environment; the repo's own `pg`
 * dependency is used instead.
 */
const fs = require('node:fs');
const path = require('node:path');

const REPO = process.env.OPENMAIC_REPO || '/data/workspace/reese/projects/OpenMAIC';
const OUT_DIR = process.argv[2] || '/tmp/openmaic-interactive-pages';
const { Client } = require(path.join(REPO, 'node_modules', 'pg'));

/** Tags whose CONTENT KaTeX's auto-render never looks at. */
const IGNORED_TAGS = ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'];

function stripIgnoredContent(html) {
  let out = html;
  for (const tag of IGNORED_TAGS) {
    const re = new RegExp(`<${tag}\\b[^>]*>[\\s\\S]*?</${tag}\\s*>`, 'gi');
    out = out.replace(re, ` <${tag}>…</${tag}> `);
  }
  return out;
}

function countMatches(text, re) {
  return (text.match(re) ?? []).length;
}

function report(html) {
  const body = stripIgnoredContent(html);
  const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)]
    .map((m) => m[1] ?? '')
    .join('\n');

  return {
    legacyCdnBlock: /cdn\.jsdelivr\.net\/npm\/katex/i.test(html),
    katexMentions: countMatches(html, /katex/gi),
    bodyDisplayMath: countMatches(body, /\$\$/g),
    bodyInlineMath: countMatches(body, /(?<!\$)\$(?!\$)/g),
    bodyParenMath: countMatches(body, /\\\(/g),
    bodyBracketMath: countMatches(body, /\\\[/g),
    scriptDollar: countMatches(scripts, /\$/g),
    scriptExplicitMath:
      countMatches(scripts, /katex\s*\.\s*render|renderMathInElement/g) +
      countMatches(scripts, /\\\([^)\n]*?\\\)/g) +
      countMatches(scripts, /\\\[[^\n]*?\\\]/g) +
      countMatches(scripts, /\$\$[^$\n]+\$\$/g),
  };
}

(async () => {
  const url = process.env.DATABASE_URL;
  if (!url) {
    console.error('DATABASE_URL is not set. Load .env.local first.');
    process.exit(2);
  }
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const client = new Client({ connectionString: url });
  await client.connect();
  const { rows } = await client.query(
    "select stage_id, id, scene_order, data from document_scenes " +
      "where data->>'type' = 'interactive' order by stage_id, scene_order",
  );
  await client.end();

  if (!rows.length) {
    console.log('No stored interactive scenes.');
    return;
  }

  const columns = [
    'stage',
    'order',
    'id',
    'bytes',
    'legacyCdn',
    'katexRefs',
    'body$$',
    'body$',
    'body\\(',
    'body\\[',
    'script$',
    'scriptMath',
  ];
  console.log(columns.join('\t'));

  for (const row of rows) {
    const html = row.data?.content?.html || '';
    const file = path.join(OUT_DIR, `${row.stage_id}_${row.scene_order}_${row.id}.html`);
    if (html) fs.writeFileSync(file, html);
    const r = report(html);
    console.log(
      [
        row.stage_id,
        row.scene_order,
        row.id,
        html.length,
        r.legacyCdnBlock,
        r.katexMentions,
        r.bodyDisplayMath,
        r.bodyInlineMath,
        r.bodyParenMath,
        r.bodyBracketMath,
        r.scriptDollar,
        r.scriptExplicitMath,
      ].join('\t'),
    );
  }
  console.log(`\nHTML written to ${OUT_DIR}`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
