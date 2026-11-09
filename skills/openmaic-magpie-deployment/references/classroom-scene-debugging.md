# Debugging a classroom scene at runtime

How to find, reproduce, and diagnose a classroom scene that misbehaves in
the browser (a runtime-error banner, a blank widget, a scene that renders
nothing) without waiting for a regeneration cycle.

## Where classroom content lives

Classroom data is in postgres, not in the repo. `DATABASE_URL` in
`.env.local` points at it (`postgres://openmaic:***@127.0.0.1:5432/openmaic`).

| Table | Holds |
|---|---|
| `document_stages` | one row per classroom: `id` (`stage-<base64url>`), `name`, `data` (jsonb) |
| `document_scenes` | one row per scene: `stage_id`, `id`, `scene_order`, `data` (jsonb) |

A scene's `data` carries `type` (`slide` / `quiz` / `interactive` / `pbl`),
`title`, and `content`. For an `interactive` scene, `content.html` is the
whole authored page — this is the string you want.

There is no `psql` binary in this environment. Query through node using the
repo's own `pg` dependency instead:

```js
// /tmp/q.cjs — run with: cd <repo> && set -a && . ./.env.local && set +a && node /tmp/q.cjs
const { Client } = require('/data/workspace/reese/projects/OpenMAIC/node_modules/pg');
(async () => {
  const c = new Client({ connectionString: process.env.DATABASE_URL });
  await c.connect();
  const st = await c.query("select id, name from document_stages order by created_at desc");
  const sc = await c.query(
    "select id, scene_order, data from document_scenes where stage_id=$1 order by scene_order",
    [st.rows[0].id],
  );
  sc.rows.forEach((r, i) => {
    const html = r.data?.content?.html || '';
    console.log(i + 1, r.data?.type, r.data?.title, 'html=' + html.length);
  });
  await c.end();
})();
```

`scene_order` is 1-based and matches the scene counter the classroom shows,
so `order=13` is the page the user calls "page 13".

## Getting the exact document the browser ran

The classroom mounts each interactive scene as a sandboxed `srcDoc` iframe
(`components/scene-renderers/InteractiveIframeHost.tsx`). The frame has no
`allow-same-origin`, so the parent cannot read `contentDocument` — but the
**`srcdoc` attribute is readable from the parent DOM**:

```js
const big = Array.from(document.querySelectorAll('iframe'))
  .map(f => f.getAttribute('srcdoc'))
  .filter(Boolean)
  .sort((a, b) => b.length - a.length)[0];
```

That string is `patchHtmlForIframe(sourceHtml)` — the authored HTML plus the
shims from `lib/utils/iframe.ts` (error capture, element picker, storage
shim, iframe CSS) and the observation reader. **Its line numbers are what the
browser reports**, so a browser error citing `about:srcdoc:399` refers to
this string, not to the stored `content.html`.

Recompute it offline (same function, no browser) when you want the artifact
without a live classroom:

```ts
// repo root; needs the repo's tsconfig paths
import { patchHtmlForIframe } from '@/lib/utils/iframe';
import fs from 'node:fs';
fs.writeFileSync('/tmp/scene.html', patchHtmlForIframe(fs.readFileSync('/tmp/raw.html', 'utf8')));
```

`node_modules/.bin/tsx` runs it; put the script inside the repo so the
`@/` alias resolves.

## The runtime-error banner pipeline

A browser error inside the frame becomes the classroom banner
(「这个互动未能运行」) through this chain:

1. `lib/utils/iframe.ts` `ERROR_CAPTURE_SHIM` — injected as the very first
   script, so it observes everything after it. It listens for `error`,
   `unhandledrejection`, and patches `console.error`, then
   `postMessage`s `{__maicInteractive:true, kind:'runtime-error',
   errorKind, message}` to the parent.
2. `components/scene-renderers/InteractiveRuntimeErrorBanner.tsx` renders it
   (i18n key `chat.interactiveRuntimeError.title`).
3. `components/scene-renderers/InteractiveIframeHost.tsx` receives the
   message and stores it per scene in `useSceneRuntimeErrors`.

So the banner text is the iframe's own error message. To see the errors a
scene emits, listen on the classroom page for the same message shape:

```js
window.__errs = [];
addEventListener('message', e => {
  if (e.data?.__maicInteractive && e.data.kind === 'runtime-error')
    window.__errs.push([e.data.errorKind, e.data.message]);
});
```

Install it **before** the scene mounts (the pool keeps iframes alive across
scene switches, so a listener added after the error fired never sees it).
The shim also buffers and replays on request: the host sends
`{__maicErrorReplayRequest:true}` to the frame once its listener is ready.

## Third-party CDN in generated interactive pages

`packages/@openmaic/generation/src/interactive-post-processor.ts`
(`postProcessInteractiveHtml`) injects a KaTeX auto-render block into every
generated interactive page that does not already mention `katex`:

- `<link>` + two `<script src>` pointing at `cdn.jsdelivr.net` for the KaTeX
  stylesheet, `katex.min.js`, and `contrib/auto-render.min.js`;
- an inline script that calls the global `renderMathInElement(...)` on
  `DOMContentLoaded`, inside a `MutationObserver` and a 2s polling loop.

Consequences worth knowing before changing anything:

- `renderMathInElement` exists **only** if `auto-render.min.js` loaded. If
  the CDN is unreachable, the unguarded call throws
  `ReferenceError: renderMathInElement is not defined` and the page dies.
  The sibling dependencies in the same page are guarded by the page author
  (`typeof loadPyodide !== 'function'`, `if (window.CodeMirror)`); this
  injected block is not.
- The injection must be **conditional**: a page whose body holds no math
  must not ask for the CDN at all, because a failed request then costs the
  whole page instead of only the formulas. And every call to
  `renderMathInElement` must be guarded with an explicit
  `typeof renderMathInElement !== 'function'` check — the page author's own
  dependencies are guarded the same way, and this injected block is not.
  Before assuming a page needs KaTeX, strip `<script>` blocks and check the
  visible body for `$` / `$$` / `\(` / `\[`.
- The **export and video-export** paths are not affected: they run the page
  through `inlineHtmlAssets` (`lib/export/inline-assets.ts`), which rewrites
  external scripts and styles into `data:` URIs, and their CSP
  (`lib/export/standalone-html/assemble.ts`,
  `render-service/src/untrusted-html-csp.ts`) allows `data:` but not
  `https:`. Only the live classroom path leaves the CDN reference intact.
- The render-service preview path is a **separate** rejection: the preview
  validator (`render-service/src/preview-validation.ts`,
  `findNonSelfContainedInteractiveReferences`) refuses any interactive page
  that still references a non-self-contained URL, so a page carrying a CDN
  KaTeX block cannot be previewed at all. That is a distinct failure from
  the classroom banner.

## Where an interactive page's HTML is transformed

Every consumer of an interactive page's `content.html` passes through one of
these seams. Know them before choosing where to fix or repair a page:

| Seam | File | Covers |
|---|---|---|
| Render funnel | `lib/utils/iframe.ts` `patchHtmlForIframe` | classroom iframe pool, thumbnail, standalone export, video export — all four |
| Server read | `lib/persistence/owner-bound-document-store.ts` `sanitizedDocument` / `getScene` | classroom load, preview, agent tools |
| Client read | `lib/edit/slide-schema.ts` `migrateInteractiveContent` (via `lib/store/stage.ts`) | store-boundary normalization of any incoming scene |
| Generation | `packages/@openmaic/generation/src/scene-generator.ts` | newly generated pages only |

Consequences:

- `patchHtmlForIframe` is the single render funnel for all four client
  sinks — a repair there reaches every one of them.
- `lib/sanitize/scene-content.ts` is **not** a seam for interactive pages:
  its walker only touches slide elements (`text` / `shape` / `table` /
  `latex`), never an `interactive` content kind.
- Changing the generation-time post-processor does **not** change pages
  already in the database. Those carry the old bytes and need a read-path
  repair (server read seam + client migration seam) or a data migration;
  repairing at the read path is idempotent and needs no migration.

## Detecting math the way KaTeX does

"Does this page need KaTeX" is not "does the HTML contain the word katex"
and not "how many `$` are in the page". KaTeX's auto-render:

- ignores the **content** of `script`, `noscript`, `style`, `textarea`,
  `pre`, `code`, `option` (its default `ignoredTags`);
- matches delimiters longest-first — `$$` before `$`, with `\[`/`\]` and
  `\(`/`\)` independent — and a closing delimiter only ends the formula at
  brace level zero;
- renders **one text node at a time**, so a delimiter cannot span an
  element boundary, and it merges adjacent sibling text nodes — so scan
  text nodes, never the document as one string.

A script body may still contribute math, but only when explicit: a
`katex.render` / `renderMathInElement` call, a `\(...\)` / `\[...\]` /
`$$...$$` pair, or a `$...$` pair whose content can only be a formula. An
arbitrary `$` in a script is JavaScript (a jQuery call, a template
interpolation), never a formula.

Measure against the **real** stored pages before trusting a detector: in
practice every `$` in a generated page is JavaScript (`$('canvas')`,
`${phase()}`), so a naive `$` count reports math on pages that have none.
`scripts/scan-interactive-katex.cjs` dumps every stored interactive page and
prints that split (body delimiters vs. script delimiters vs. legacy CDN
block), so a detector can be validated against real content in one run.

## Package boundaries when touching this area

- `@openmaic/generation` is listed in `next.config.ts`
  `serverExternalPackages`: the server loads its **built** `dist/` natively
  instead of bundling it. A source edit under that package has no runtime
  effect until `pnpm run build:packages` rebuilds it.
- The browser-safe entry is `@openmaic/generation/browser`; it is already
  imported from client code, so a helper that must run in the browser
  belongs there rather than in the root barrel (the root barrel also exposes
  Node-only prompt loaders).
- Shared, dependency-free helpers that both client and server need belong
  in `@openmaic/dsl` (it already hosts the KaTeX options helper
  `safeKatexOptions`). Moving code into DSL triggers the DSL version rules
  in `scripts/check-package-version-bumps.mjs` — a format-constant change
  forces a minor/major bump with a caret-escape check on dependents.
- Every `@openmaic/*` package whose publishable inputs change must ship a
  version increase; the check script enforces it.

## Guard that any change must satisfy

`tests/math/math-engine-guard.test.ts` scans every product source file for
a path to a math renderer (direct import of `katex`/`temml`/…, or KaTeX
auto-render injected as script text). Files allowed to reach a renderer are
listed in its `ALLOWLIST`, each with a `kind` and a reason string; anything
unlisted fails the suite, and a stale allowlist entry also fails. The
interactive post-processor is currently listed as `reviewed`.

Any edit to how the post-processor injects or guards KaTeX must update that
entry's reason to match the new behaviour, and the guard test must still
pass.

## Reproducing an interactive page outside the classroom

The fastest loop: write the authored HTML to a scratch dir, serve it with
`python3 -m http.server`, and load it in a browser tab with a hook that
records `window.onerror` and the `typeof` of the globals in play. To simulate
a CDN outage, block the URL with CDP
(`Network.enable` + `Network.setBlockedURLs`) on the **same target** you then
reload, and clear the block with `urls=[]` before measuring the healthy
baseline — the setting survives reloads.

## Probing many stored pages at once

To survey every stored interactive page across every course (not just the
newest one), filter on the stored discriminant instead of walking one
stage's scenes:

```sql
select stage_id, id, scene_order, data from document_scenes
where data->>'type' = 'interactive' order by stage_id, scene_order
```

Then measure each page's `data->'content'->>'html'`.

Two mechanics that decide whether a survey survives:

- **Put the probe in a script file, not in an inline shell heredoc.** A
  multi-line probe written through a shell heredoc or an inline string gets
  its quoting mangled and fails for reasons unrelated to the probe. Write
  the file with the file-writing tool, then run it with
  `npx tsx <file>` from the repo root (the repo's `tsconfig` paths only
  resolve for scripts inside the repo) or `node <file>` for plain CommonJS.
- **Write the survey's output to a file and read it back.** A probe whose
  result is dozens of rows (per page, per field) is worth far more as a
  file you can re-read and grep than as console output you have to capture
  in one shot. If a step's output may be truncated, redirect it
  (`... > /tmp/report.txt 2>&1`) and read that file in the next step.

Both keep a survey's result **recoverable** — a multi-step survey whose
intermediate output is only visible once cannot be checked, and a survey
that cannot be checked is indistinguishable from a survey that found
nothing.
