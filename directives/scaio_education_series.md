# Directive: SCAIO Education Series (Learn 2.0)

> Living SOP. Update the **Learnings** section as you go. Do not rewrite the goals, structure, editorial rules, or approval gate without asking Jimmy.
> Companion to `directives/scaio_content_agent.md`. That directive's **Voice & editorial rules** and **Hard rules** apply here in full; this file only adds what is specific to the education series.

## Goal

Turn SCAIO Learn from a shelf of 13 audience primers into a guided education hub:

1. **The AI Learning Map:** an interactive "start here" page that lays out the whole field as nine branches. Each branch has subtopics, a three-level reading path (Curious → Practitioner → Builder), the SCAIO primers and articles that belong to it, and a short self-check quiz.
2. **Who's Who in AI:** a plain-language reference to the organizations that shape AI (Nvidia, Hugging Face, Anthropic, TSMC, NIST, and so on). It ships as a searchable directory page plus one 10-minute primer deck.
3. **A reorganized Learn page:** three tiers, Map (start here) → Primers (by audience) → Reference shelf (term glossary + Who's Who).
4. **A resource library:** every resource on the map in one filterable page (branch, type, level, free/paid).
5. **New primer decks rebuilt from the Gemini Notebook material**, starting with "How an LLM is built."
6. **A social stream:** one bite-sized post per organization and per branch, queued through the existing content-agent pipeline.

Everything ships through **pull requests**. Nothing merges or posts without Jimmy.

## Context

- The site is plain HTML on GitHub Pages. See the content-agent directive's Learnings for repo layout. Primers live in `learn/` and share `learn/deck.css` and `learn/deck.js`. **Reuse those.** Do not create a second design system.
- Design tokens: the `:root` variables in `learn/deck.css` and `learn/index.html` (navy `#081a36`, blue `#0b4ea2`, bg `#f6f8fb`, Inter). New pages match the existing Learn page look exactly.
- The 13 current primers and their audiences are listed on `learn/index.html`. Primers stay audience-based. The map links to them; it does not replace them.
- `index.html` line ~1565 still says "Browse all 10 primers" while Learn lists 13. Fix that in the first PR. Better yet, generate the count from the primer list so it can't drift again.

## Inputs

Put inputs in `directives/inputs/education/`. That folder is excluded from the public site because `directives/` is already excluded in `_config.yml`.

| File | What it is | How to treat it |
|---|---|---|
| `learning_map_source.md` | Jimmy's "SCAIO AI Learning Map" outline: 9 branches, subtopics, sources by level. Exported from the Claude doc. | **Canonical structure.** Branch names, subtopics, and level assignments come from here. |
| `gemini/` (optional) | Anything from Gemini Notebook: a pasted interactive report, exported report text, mind-map JSON, quiz CSV, or a public notebook link in `gemini/LINK.txt`. | **Draft raw material only.** Use it for phrasing ideas, quiz questions, and gaps the outline missed. AI-generated content. Never copy it in unverified, never let it override the canonical structure, and never embed Google's viewer or link to the notebook from the site unless Jimmy says so. |
| `whos_who_seed.md` (optional) | Any org list Jimmy adds. | Merge with the starter list below. |

If a public Gemini notebook link is provided and can't be fetched by script, note it in the PR and work from whatever has been pasted into `gemini/`. Don't try to scrape around it.

## Deliverables

### 1. The AI Learning Map: `learn/map.html`

An interactive report in SCAIO's design, built from the same pattern as Gemini's interactive reports: prose sections with interactive blocks embedded between them.

- **Top:** a short lead, then a **mind map** of the nine branches and their subtopics. Render it with [markmap](https://markmap.js.org) (MIT), loaded from `cdn.jsdelivr.net`, generated from a nested markdown outline embedded in the page. Clicking a branch node scrolls to that branch's section.
- **One section per branch.** Each one has:
  - Two or three sentences on what the branch covers and why it matters to South Carolina.
  - The subtopics as a compact list.
  - A **reading path** table with three columns (Curious / Practitioner / Builder). Each resource gets one line: title, type (course, video, book, report, newsletter), free/paid.
  - **"From SCAIO":** the relevant primers rendered as cards. Clicking a card opens the existing deck in an inline modal (`<iframe>` of the primer page, keyboard navigation intact) with an "Open full screen" link. Do not duplicate deck content.
  - A **3–5 question self-check** (multiple choice, plain JS, no storage, instant feedback with a one-line explanation). Questions must be answerable from SCAIO content or the cited sources.
- A "Staying current" section at the end. Keep it short.
- **Figures:** where a branch benefits from a diagram (for example, the chip-to-power infographic in Infrastructure), draw it as inline SVG in SCAIO's design. Don't use Gemini's images. No company logos; use plain labels instead.
- Data lives in `learn/map-data.json` (branches, subtopics, resources, quiz items), and the page renders from it. Future updates are then data edits, not HTML surgery.
- Must work on phones (16px gutters, no horizontal scroll), with keyboard and screen readers (mind map has a text-list fallback), and with no build step.

### 2. Who's Who in AI

- **`learn/whos-who.html`:** a searchable, filterable directory. Filters: stack layer (Frontier labs, Chips & hardware, Cloud & compute, Platforms & open source, Applications, Research & nonprofits, Government bodies). Data in `learn/whos-who.json`.
- **Entry template** (every field required unless marked optional):
  - `name`, `layer`, `hq` (city, country), `founded`
  - `what_they_do`: one or two plain sentences, no jargon
  - `why_it_matters`: one sentence
  - `sc_angle` (optional): a sourced South Carolina connection, e.g., a facility, investment, or partnership. Link to the SCAIO Ecosystem entry or article where one exists.
  - `official_url`, `sources` (fetched URLs backing each fact), `last_verified` (date)
- **`learn/primer-whos-who.html`:** a 10-minute deck on `deck.css`/`deck.js`. One slide per stack layer, showing who's in it and how the layers depend on each other, ending with a slide on the SC footprint. It's the global counterpart to `primer-10-sc-landscape.html`.
- **Starter list (~30):** OpenAI, Anthropic, Google DeepMind, Meta AI, xAI, Microsoft, Mistral, DeepSeek, Alibaba (Qwen), Nvidia, AMD, Intel, Broadcom, TSMC, ASML, Amazon Web Services, Google Cloud, Oracle, CoreWeave, Hugging Face, GitHub, Ollama, Perplexity, Cursor (Anysphere), Allen Institute for AI, EleutherAI, Stanford HAI, NIST / Center for AI Standards and Innovation, UK AI Security Institute, EU AI Office.
- Keep this separate from the SC **Ecosystem** directory, which stays SC-only. Cross-link both ways where an organization has an SC footprint.

### 3. Learn page reorganization: `learn/index.html`

- New top band: "Start here: The AI Learning Map", linking to `map.html`.
- The existing primer grid stays as is, grouped under "Primers by audience."
- New "Reference shelf" band: the legislator's glossary (moved from the grid, or listed in both places), Who's Who, and the term glossary.
- Update the homepage Learn section and its primer count to match.
- **This is a design change.** Open it as its own PR, titled `[DESIGN] Learn reorganization`, with screenshots (desktop and phone) in the description.

### 4. Resource library: `learn/library.html`

- One page listing every resource in `map-data.json` (branch reading paths plus Staying current), rendered from that file. No second copy of the data.
- Filters: branch, level (Curious / Practitioner / Builder), type (course, video, book, podcast, newsletter, report, paper, data, guide), and free/paid. Plus a text search.
- Each row shows: title, type, level, branch, free/paid, note. SCAIO items get the same "From SCAIO" mark the map uses.
- Each map branch section links to the library pre-filtered to that branch (`library.html#branch=infrastructure`).

### 5. New primer decks from the Gemini Notebook material

- The Gemini deck "Decoding the Glass Engine" (`directives/inputs/education/gemini/media/`) becomes **`learn/primer-llm-built.html`, "How an LLM is built"**, on `deck.css`/`deck.js`. Keep the storyline: next token → embeddings → layers → gradient descent → RNN vs. transformer → attention → pretraining → fine-tuning → RLHF/Constitutional AI → scaling.
- Redraw every diagram as inline SVG. Fix the source's errors before shipping: attention does not give "infinite" context or "perfect" memory; transformers do not "scale infinitely"; scaling laws are empirical trends, not "mathematically proven"; the RLHF loop has four distinct steps.
- It sits in the "How LLMs work" branch next to primer 01 and goes deeper than it. Primer 01 stays as is.
- Gemini audio and video overviews stay off the site.

### 6. Social stream

- After the Who's Who PR merges, generate queue files in `social/queue/` using the existing content-agent format and `scaio_social_post.py`. Do not build a second poster.
- Posts: one per organization, plus one per map branch. 40–120 words, plain data-describing voice, one link back to the entry or branch anchor.
- Cap the stream at 3 education posts per week so it doesn't crowd out the policy content. Spread them across the queue with a `not_before` date if the poster supports it. If it doesn't, add that support in its own small PR and record it in Learnings.

## Editorial rules (in addition to the content-agent rules)

- **Neutral on companies.** Describe what organizations do. Don't rank them, don't pick winners, don't repeat marketing claims ("leading," "revolutionary"). The same no-dunking rule that applies to officials applies to companies.
- **Verify every link and fact.** Fetch each resource URL before including it. Drop dead links. Record `last_verified`. For facts like founding year, HQ, and SC presence, cite a fetched source. If a fact can't be verified, leave it out.
- **Resources:** prefer free and official sources. Mark paid items. No affiliate links. At most one paywalled item per level per branch.
- **Plain language.** Curious-level text assumes no math and no code.
- **AI-generated input (Gemini or otherwise) is a draft.** It goes through the same verification as anything else.

## Build order (one PR each, in this order)

1. **Fixes + scaffolding:** fix the primer count and create `learn/map-data.json` from `learning_map_source.md`, with every link checked. Report dead or redirected links in the PR.
2. **Who's Who data + directory page.**
3. **Who's Who primer deck.**
4. **Learning Map page** (mind map, sections, primer modals, quizzes).
5. **`[DESIGN]` Learn reorganization + homepage update.**
6. **Social queue** for Who's Who and map branches.
7. **Resource library page** (after the map page; reads the same data).
8. **"How an LLM is built" primer deck.**

Before step 4, open a **prototype PR** with only two branches built out (Using AI, and Infrastructure) so Jimmy can approve the look before the other seven get built.

## Maintenance

- Quarterly link check across `map-data.json` and `whos-who.json`: one PR listing dead links, replacements, and stale `last_verified` dates. Add it as a mode to `scaio_run.py`, or as a small `execution/scaio_link_check.py`. Check `execution/` first.
- When a new primer or Journal article ships, the content agent proposes where it slots into the map in that PR's notes.

## Hard rules

- Never push to `main`. Every change goes through a PR.
- Do not change the design of existing primers, articles, or the homepage beyond what a `[DESIGN]` PR explicitly says.
- Do not embed or iframe Google/Gemini Notebook content on the site.
- Ask Jimmy before anything that spends beyond normal Claude API drafting (paid data, image generation).
- Do not create or overwrite other directives without asking.

## Open questions for Jimmy

1. Should the term glossary stay legislator-focused, or get a general-audience version next to Who's Who?
2. Quiz scores: keep them stateless (current plan), or let readers save progress in their own browser?
3. Should education posts go to both LinkedIn and Facebook, or LinkedIn only?

## Learnings

_(Append dated entries.)_

### 2026-10-15
- **Gemini Notebook material arrived.** The report text is in `inputs/education/gemini/report.md`. The deck PDF, mind-map PNG, infographic, audio (1:47) and video (7:52) are in `gemini/media/`, which is gitignored (53 MB of video). The NotebookLM share link can't be fetched (Google sign-in), so copy-paste and downloads are the only route.
- **Jimmy decided: rebuild, don't host.** No Gemini images, audio, or video go on the site. The deck is rebuilt as a SCAIO primer and the infographic as an SVG figure. Added the resource library page (deliverable 4) at Jimmy's request.
- **Gemini's mind map matches `learning_map_source.md` node for node**, so the canonical structure needs no changes.
- **The Gemini report text needs an editorial pass before reuse.** Hype words ("revolutionary," "seminal," "giants"), an unsourced water figure, and prompt injection filed under "Malfunction." Check that last one against `scaio-article-map-of-ai-risk.html`.
- **The prototype PR was opened right after step 1,** ahead of Who's Who, so the look gets approved early. It is still the gate for the full map page.

