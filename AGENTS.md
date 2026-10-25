# RC150 Autonomous Coding Agent — Project Instructions

## Mission
Maintain and improve the RC150 Department Registration Ranking Dashboard:
- Live dashboard: https://natchplaize-oss.github.io/rc150/
- Official public source: https://rc150.org/bn/profiles
- Repository: https://github.com/natchplaize-oss/rc150

## Project context and decisions
1. The dashboard is a GitHub Pages project. Current repository includes `index.html`, `stats.json`, `scripts/update_stats.py`, and GitHub Actions workflows.
2. A scheduled workflow runs the aggregate-count updater every five minutes.
3. The updater currently extracts only the overall registration total. Department counts in `stats.json` are deliberately `null`; do not treat them as zero and do not fabricate counts.
4. The intended dashboard must show verified department-wise registration counts, rankings, charts, highest/lowest counts, and the overall count.
5. Department/group options currently include 32 department labels and 10 group labels in `stats.json`. Normalize spelling/capitalization variants only when doing so preserves the original source's meaning; avoid counting aliases as separate departments unless the source distinguishes them.
6. The dashboard should refresh in the browser every 30 seconds if appropriate, while source statistics are refreshed automatically by the scheduled workflow.
7. The original requirement is that no unverified or invented statistics should be shown as factual data.
8. Conversation history established the main blocker: the official site's department filter/data source must be inspected to discover whether an API or other structured source can provide complete records. If no API is available, evaluate public profile pagination and filters.

## Reverse-engineering requirement (explicit)
The agent must be capable of systematic, authorized reverse engineering of the public RC150 website's observable front end, because discovering how its department filters work is a core project requirement.

### What it should inspect
- Public HTML and DOM structure, rendered forms, filter labels/options, pagination controls, and accessible page metadata.
- JavaScript and CSS files loaded by the browser, including publicly served source maps when available.
- Publicly observable browser Network requests (Fetch/XHR/document requests), request URLs and methods, query parameters, response status/content types, and publicly returned JSON or HTML that powers the filters.
- Public robots.txt, sitemap, and publicly documented endpoints where relevant.
- Whether the department filter changes the URL, query string, page contents, or pagination, and whether filtered results can be counted consistently.
- Reproduce requests only when they are publicly accessible and authorized; use conservative request rates and validate results against the visible site.

### Boundaries and technical truth
- The browser Inspect/DevTools panel exposes the page's client-side code and browser-visible traffic; it does not reveal private server-side source code or database internals.
- Do not attempt to bypass login, CAPTCHA, access controls, anti-bot measures, rate limits, or exploit vulnerabilities. Do not access non-public data.
- Do not claim to have inspected every code file unless the actual files and requests were enumerated and checked. Record which resources were inspected and which were inaccessible.
- If a public API endpoint is found, document the endpoint shape, required public parameters, response schema, pagination, limits, and a repeatable validation method. Never put private credentials in source code.
- If no usable API is found, implement and test a fallback collector using the public filter and pagination, provided the site permits it.
- Treat the RC150 site as the source of truth for observed behavior; never assume that the dashboard's own code reveals the official site's internal implementation.

## Reverse-engineering acceptance criteria
Before declaring this requirement complete, provide a reproducible report containing:
1. Public page and assets examined.
2. Filter controls and option values identified.
3. Relevant public requests/endpoints found, or a clear record that none was discoverable through permitted inspection.
4. Pagination and response schema behavior.
5. Test results comparing at least a sample of collected results with the official page.
6. Known limitations and the next concrete implementation step.

## Required agent behavior
- Inspect the existing code and current data before editing.
- Work in small, reviewable changes; preserve working functionality.
- Run available tests, syntax checks, and data validation after changes.
- Never expose credentials, tokens, or secrets in logs or commits.
- Never bypass authentication, CAPTCHAs, rate limits, or access controls. Use only publicly accessible data and respect the source site's terms and reasonable request rates.
- Do not invent department counts. Record provenance, retrieval time, completeness, and errors.
- Handle pagination completely and detect duplicate profiles before computing aggregates.
- Normalize department names conservatively and document alias mappings.
- If collection is partial or fails, preserve the last verified data and clearly mark the update as unsuccessful/stale rather than replacing verified values with guesses.
- Do not silently change the meaning of the overall count or department list.
- Report exactly what changed, what tests ran, and what remains blocked.

## Autonomous execution architecture
GitHub Actions can run scripts and tests automatically. A language-model coding agent that writes new code autonomously additionally requires a configured model/API credential and an explicit workflow. Never assume such credentials exist; check configuration without printing secret values. Any workflow must use least-privilege permissions and avoid committing secrets.

## Initial priority
1. Inspect `index.html`, `stats.json`, `scripts/update_stats.py`, and existing workflows.
2. Determine the official profiles page's form/filter implementation and any publicly exposed structured data endpoint.
3. Prototype a polite, bounded collector against public pages; validate its results against the site's visible filters and total.
4. Add tests for pagination, duplicate detection, department aliases, incomplete runs, and preserving the last good dataset.
5. Only then populate department counts and rankings.
