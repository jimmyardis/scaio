# Directive: SCAIO Content Agent

> Living SOP. Update the **Learnings** section as you discover API limits, edge cases, or better approaches. Do not rewrite the goals, voice, or approval rules without asking Jimmy.

## Goal

Keep scaio.org and SCAIO's social channels current with accurate, nonpartisan, well-sourced coverage of AI policy and adoption in South Carolina, with minimal effort from Jimmy. The agent does the monitoring, drafting, and packaging. **Jimmy approves everything before it goes public.**

The single approval gate is a **GitHub pull request**. If Jimmy merges it, the content is published and social posts go out. If he closes it, nothing happens. He should be able to review and merge from his phone in under 10 minutes.

## Context

- **Site:** scaio.org is a static site published from GitHub (GitHub Pages). Publishing means committing new or changed files to the repo.
- **Chatbot:** The SCAIO Policy Navigator (RAG chatbot) runs on Railway. New published content should eventually feed its corpus (see Phase 3).
- **Editorial foundation:** The post "Everywhere at Once: What South Carolina's AI Committee Is Really Up Against" (Sept 18, 2026) sets SCAIO's core position:
  - AI is hard to govern because of breadth times velocity.
  - Expertise is split by domain and decays over time.
  - Institutions should learn continuously: start with the state's own AI use, govern harms through existing law, build standing capacity instead of relying on one-time reports, and learn from other states.
  - All content should be consistent with this position.
- **Anchor story:** The SC Senate Special Committee on Artificial Intelligence (chair: Sen. Tom Young) began a roughly two-year study on Sept 16, 2026, with recommendations targeted for Sept 2028. Tracking this committee is a standing priority.

## Content pillars

1. **Committee & Legislature Tracker.** Committee meetings, testimony, AI-related bills, and votes, covering both the Senate and House.
2. **State Government Use.** How SC agencies, local governments, and schools are adopting AI, including procurement, pilots, and policies.
3. **Other States & Federal.** Relevant moves by other states and federal action that affects SC, including preemption.
4. **Explainers.** Short, plain-language pieces that answer questions lawmakers and residents are actually asking.
5. **Intersection Voices** (occasional). Perspectives from people who work where AI meets a specific field.

## Voice & editorial rules

These are non-negotiable:

- **Nonpartisan and constructive.** Never mock, dunk on, or single out lawmakers. Frame problems as structural, not personal. SCAIO's credibility with legislators of both parties is the asset.
- **Sourced.** Every factual claim gets a numbered citation to a primary or reputable source, using the same footnote format as the "Everywhere at Once" post. Primary sources come first: scstatehouse.gov, committee pages, agency sites, and official documents.
- **Paraphrase, don't copy.** Never reproduce article text. Quotes from any single source must be under 15 words, and each source may be quoted at most once. Default to paraphrase.
- **No fabrication.** If a fact can't be verified from a fetched source, leave it out. Never invent quotes, numbers, dates, or attributions. Flag uncertainty in the PR description.
- **Plain language.** Write for a smart non-specialist, like a legislator's aide or a local reporter. Short paragraphs. No hype and no doom.
- **Name people accurately.** Use correct titles and districts, and verify spellings against official rosters.

## Cadence

| Run | Trigger | Output |
|---|---|---|
| Weekly roundup | GitHub Actions cron, Mondays 7am ET | One PR containing a site post (weekly brief) plus 2–3 social drafts |
| Event run | Committee meeting or major bill action detected | One PR containing a short update post plus 1–2 social drafts, opened within 24h |
| Evergreen | Monthly, first Wednesday | One PR containing an explainer or state-comparison piece |

If there is nothing substantive in a given week, **open no PR**. Send Jimmy a one-line "quiet week" note instead. Never pad.

## Pipeline

Before building anything, **check `execution/` for existing scripts**. The email and social automation built under Jimmy's internal-systems work may already cover posting or digests. Reuse or extend those instead of duplicating them.

### 1. Monitor: `execution/scaio_monitor_sources.py`

- **Inputs:** `directives/scaio_sources.yaml`, a list of sources with URL, type (rss/html/api), and pillar.
- **Starting sources** (verify each endpoint works and record it in Learnings):
  - SC Legislature (scstatehouse.gov): bill search and status for AI-related terms, plus committee meeting schedules and agendas.
  - SC Senate Special Committee on AI page and meeting notices.
  - Governor's office and SC Dept. of Administration (state IT and AI policy).
  - NCSL AI legislation tracking (for other states).
  - SC news: Post and Courier, The State, SC Daily Gazette, Live 5, WIS, ABC Columbia, WSPA, and WRDW. Prefer RSS feeds.
  - Federal: Federal Register and White House items that match AI preemption or state-law terms.
- **Behavior:**
  - Fetch sources and filter by keywords such as "artificial intelligence", "AI", "machine learning", "deepfake", "synthetic media", and "algorithm".
  - Deduplicate against `.tmp/scaio_seen.json`.
  - Classify each item by pillar and score it for relevance.
- **Output:** `.tmp/scaio_items_YYYY-MM-DD.json`

### 2. Draft: `execution/scaio_draft_content.py`

- **Inputs:**
  - The items JSON from step 1.
  - The editorial rules in this directive.
  - The site's post template, discovered from the repo. Match the existing structure, front matter, and CSS classes. Use the "Everywhere at Once" post as the reference implementation.
- **Behavior:**
  - Call the Claude API to draft the post and social variants.
  - Fetch every cited source and confirm the claim appears in it before including it. Drop any claim that can't be verified.
- **Outputs:**
  - The post HTML, in the correct repo path.
  - Updates to the post index, sitemap, and RSS feed, if the site has them.
  - `social/queue/YYYY-MM-DD-<slug>.json`, containing one entry per platform with text, link, and any image path. Respect platform length limits.
  - `.tmp/scaio_draft_notes.md`, listing uncertainties, dropped claims, and suggested edits. This goes into the PR description.

### 3. Package: `execution/scaio_open_pr.py`

- Create a branch named `content/YYYY-MM-DD-<slug>`, commit the files, and open a PR.
- **PR description:**
  - A one-paragraph summary of what's new.
  - The social drafts, pasted inline so Jimmy can read everything in one place.
  - The draft notes, including uncertainties.
  - A checklist: facts verified, tone check, links working.
- Request Jimmy as reviewer so the GitHub mobile app notifies him.

### 4. Publish on merge: GitHub Action `.github/workflows/scaio_publish.yml`

- On merge to `main`, GitHub Pages deploys the site automatically.
- The Action then runs `execution/scaio_social_post.py`. It reads any new files in `social/queue/`, posts them, and moves them to `social/posted/` with timestamps and post URLs.
- **Posting method:** use a scheduler API (e.g., Buffer) or native platform APIs. **Confirm platforms and method with Jimmy before building.** See Open questions.
- Edits Jimmy makes to the social JSON before merging are respected, because the merged file is the source of truth.

### 5. Digest: `execution/scaio_digest.py`

- After each run, send Jimmy a short email with the PR link, a two-line summary, and anything flagged.
- If no PR was opened, send the "quiet week" note instead.
- Reuse existing email tooling if it's already in `execution/`.

## Phase 3 (later): Feed the Policy Navigator

On merge, push new post text and source metadata to the Railway chatbot's ingestion path, so the Navigator can answer questions about recent developments. **Investigate the existing ingestion setup before building, and ask Jimmy before changing the Railway deployment.**

## Environment (`.env`)

- `ANTHROPIC_API_KEY`
- `GITHUB_TOKEN`. In Actions, use the built-in token or a fine-grained PAT scoped to the scaio.org repo.
- `SCAIO_REPO` (owner/name)
- Social credentials (e.g., `BUFFER_ACCESS_TOKEN` or per-platform keys), once platforms are confirmed.
- Email credentials for the digest (reuse existing).

Secrets used by Actions go in GitHub repository secrets, never in committed files.

## Hard rules

- **Never push directly to `main`.** Every change goes through a PR.
- **Never post to social media except through the merge-triggered Action.** Never post from a local run.
- **Paid APIs:** before running anything that spends credits beyond normal Claude API drafting (e.g., image generation or paid data sources), check with Jimmy.
- **Don't change site design, navigation, or existing posts** unless the PR is explicitly for that and says so.
- **Don't create or overwrite other directives** without asking.

## Edge cases

- **Breaking news mid-week** (e.g., a bill passes or the committee votes): run the event pipeline. Mark the PR title `[TIMELY]`.
- **Conflicting reports between sources:** say so in the post, favor the primary source, and flag it in the PR notes.
- **Source is paywalled or unreachable:** skip it and note it. Don't cite what you couldn't read.
- **Sensitive or partisan flashpoints** (e.g., an election deepfake involving a specific candidate): report facts only, with no characterization. Flag the PR for extra review.
- **Jimmy is quoted or SCAIO is mentioned in the press:** add the item to a `press` list on the site if one exists. Otherwise, flag it in the PR so he can decide.
- **A PR stays unmerged for 7 days:** close it with a note. Don't let stale PRs stack up.

## Open questions for Jimmy (resolve before building step 4)

1. ~~Which social platforms?~~ **LinkedIn + Facebook** (decided 2026-09-19). Still open: SCAIO page or personal account for each — this is just which URN/page ID goes in the secrets.
2. ~~Buffer or native APIs?~~ **Native APIs** — accounts already exist, so no Buffer layer (2026-09-19).
3. ~~Digest email?~~ **Telegram for now** (existing bot), all delivery goes through `scaio_digest.notify()` so it can move to email or Muse Agent later (2026-09-19).

## Build order

1. Inspect the scaio.org repo: structure, post template, index, sitemap, and RSS. Record findings in Learnings.
2. Build steps 1–3 and 5. Test end to end with a dry run that opens a real PR on a test branch.
3. Resolve the open questions, then build step 4 and test it with a single post.
4. Enable the cron schedule.
5. Phase 3 (Navigator ingestion) once the content pipeline is stable.

## Learnings

_(Append dated entries: API limits, source quirks, template details, failures and fixes.)_

### 2026-09-19 — initial build

**Repo & template**
- Site is plain HTML on GitHub Pages ("legacy" build from `main`, Jekyll on). No front matter, no sitemap, no RSS feed. The only post index is the homepage Journal grid (`index.html`, `#journal`); new cards go right after the `<!-- ── Published article ── -->` comment, newest first. Posts live at the root as `scaio-article-<slug>.html`.
- Reference implementation: `scaio-article-everywhere-at-once.html`. `scaio_render.build_page()` copies its `<style>`, font links, site bar, analytics and navigator widget at run time, so template changes there flow into new posts.
- `_config.yml` excludes `execution/`, `directives/`, `social/` from the public site — the repo is public and Pages would otherwise serve them.
- Weekly briefs each add a homepage card (~52/yr). If the grid gets crowded, a `/journal/` or `/briefs/` index is the fix — a design change, so ask first.

**Sources** (probed 2026-09-19; config in `directives/scaio_sources.yaml`)
- Working RSS: SC Daily Gazette, Post and Courier (search RSS), Live 5 / WIS / WRDW (Gray `arc/outboundfeeds`), ABC Columbia, WSPA, White House section feeds (`/presidential-actions/feed/`, `/news/feed/`). Station feeds only hold the latest ~20 items, so the daily event run is what keeps coverage complete.
- scstatehouse.gov: `meetings.php?chamber=S|H` (and joint) parses cleanly; the AI committee appears as "Special Senate Committee on Artificial Intelligence" with an agenda PDF under `/agendas/`. There is no dedicated committee page (the guessed URL 404s). Bill pages (`sess126_2025-2026/bills/N.htm`) have a parseable HISTORY table; tracked bills come from `bills.json`. The full-text legislation search (`query.php`) returned 0 hits for "artificial intelligence" — don't rely on it. Session 126 adjourned sine die; 127th prefiling opens Dec 2026 — add new bill URLs to `extra_bills` then.
- Governor: `governor.sc.gov/news` links match `/news/YYYY-MM/`. Admin: `admin.sc.gov/news-events/news` (`/news` 404s).
- Federal Register JSON API works without a key.
- Unreachable to scripts: The State (times out), NCSL (500, bot protection), `whitehouse.gov/feed/` (404).
- Google News search RSS is the best catch-all, but links are encrypted redirects. `resolve_google_news()` decodes them through Google's `batchexecute` endpoint (26/26 resolved on first run). If Google changes that, the items degrade to uncited "leads" listed in the PR notes — nothing breaks.
- Some outlets block scripted fetches (WLTX 403, The State timeout, Yahoo/SC Public Radio script-rendered). These get skipped and listed in the notes.

**Drafting & verification**
- Two Claude calls (`claude-opus-5`, adaptive thinking, structured JSON output, server-side refusal fallback): (1) a fact sheet where every fact carries a verbatim quote from its source; (2) the post, written only from facts that passed verification. `scaio_render.verify_facts()` checks each quote against *our own* fetch of the source. Direct quotes in the post are checked by code: under 15 words, found verbatim in a source cited in the same paragraph, at most one per source. Links are limited to fetched sources and scaio.org.
- Evergreen runs add a web-search planning call (max 8 searches, about $0.08) to pick the topic and find sources. That's the only paid tool use beyond normal drafting.
- First real weekly draft: 12 sources → 42 facts, all verified; about 35k input / 17k output tokens (roughly $0.60). It came out closer to 1,300 words than the 900 target — tighten the shape prompt if that keeps happening.
- Without Google News resolution, the same week correctly came back "not substantive" (only an agenda PDF was readable). The quiet path works.

**Operations**
- The agent's memory (`.tmp/scaio_seen.json`) persists between Actions runs through `actions/cache` (a new key each run, restored by prefix).
- For Actions to open PRs, repo Settings → Actions → General → Workflow permissions must be "Read and write" with "Allow GitHub Actions to create and approve pull requests" checked. On 2026-09-19 it was read-only.
- Local PR runs authenticate as jimmyardis via `gh`, so the reviewer request 422s: you can't request yourself. From Actions the PR author is github-actions[bot], and the request works.
- LinkedIn posting uses the Posts API (`/rest/posts`, `LinkedIn-Version` header defaults to 202608 — override with the `LINKEDIN_API_VERSION` repo variable). Posting as the SCAIO company page requires the Community Management API product (app review); posting as a person needs "Share on LinkedIn" (`w_member_social`). Facebook uses a Page access token on `/{page-id}/feed`.
