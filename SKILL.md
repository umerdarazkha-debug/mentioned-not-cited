---
name: mentioned-not-cited
description: Find the prompts where AI answers name your brand but link to someone else. Reads a CSV of AI answers (engine, prompt, answer_text, cited_urls separated by |) that you collected by hand or from any tool, plus a brand config. Reports mention rate vs citation rate per engine, the mentioned-but-not-cited prompts with the winning URLs and who owns them, a ranked list of third-party pages cited most, and page changes Claude writes for each gap. Optional server logs (Apache or Nginx combined, Cloudflare Logpush JSON) show AI bot hits and pages crawled often but never cited. Use when the user says "we are mentioned but not cited", "why does ChatGPT name us but link a competitor", "AI citation gaps", "which pages do AI bots crawl", "GEO citation audit".
---

# Mentioned, not cited

## Steps

1. Get the answers CSV with columns `engine,prompt,answer_text,cited_urls`. `cited_urls` are separated by `|`. The user can collect them by copy and paste or any export. Check each row has the real citation list, not a guess.
2. Write `brand.json`:

```json
{"brand_names": ["Acme Analytics", "Acme"], "own_domains": ["acme-example.com"],
 "competitors": [{"name": "Rivalytics", "domains": ["rivalytics.example.net"]}]}
```

   Include every spelling users might see. Matching is case-insensitive and whole word, so "Acme" does not match "Acmeville". Domains match the host or any subdomain, so `blog.acme-example.com` counts and `notacme-example.com` does not.
3. Optional: server logs. Pass each file with `--logs`. Formats: Apache/Nginx combined log format, and Cloudflare Logpush `http_requests` JSON lines (fields `ClientRequestURI`, `ClientRequestUserAgent`, `EdgeResponseStatus`, `ClientRequestMethod`).
4. Run from the skill folder:

```bash
uv run --python 3.12 scripts/mnc.py --answers answers.csv --brand brand.json \
  [--logs access.log --logs cf.ndjson] [--min-hits 3] --out report.md --json report.json
```

5. Read the report. Quote the per-engine table. A big gap between mention rate and citation rate means the model knows the brand but does not trust or find a page of yours for that prompt.
6. Write the "Suggested page changes" section yourself, one entry per gap row:
   - Fetch the winning URL and the user's best matching page (WebFetch).
   - Compare: what does the winner answer in its first screen that yours does not? Does it hold a table, price, date, number or named source yours lacks? Is yours hard to fetch (login, script-only content, slow)?
   - Write 2 to 4 concrete changes for the user's page (heading that matches the prompt, a direct answer paragraph, a data table, a dated update, schema).
   - If the winner is a third-party page (review, listicle, forum), suggest outreach or a better page instead. The ranked list shows which third-party pages to target first.
   - Do not promise results. Models change.
7. With logs: list pages crawled often but never cited. They are candidates for a rewrite or a check that the page answers a real prompt. Crawled does not mean used.

## AI bots

`references/ai-bots.json` lists tokens, purpose and the vendor page for each: GPTBot, OAI-SearchBot, ChatGPT-User (OpenAI), ClaudeBot, Claude-User, Claude-SearchBot (Anthropic publishes the token only), PerplexityBot, Perplexity-User. Google-Extended is a robots.txt token with no user agent of its own, so it never appears in logs (Google's crawler docs). Some user-triggered fetchers may ignore robots.txt, as the vendors say.

## Limits

- The answer set is a sample. Answers change run to run.
- A mention is name-in-text only. The script does not judge tone.
- Only status 200 GET or HEAD hits count for the "crawled but not cited" list. Assets and robots.txt are skipped.
- Fake bot user agents exist. Verify IPs with the vendor lists if it matters.
