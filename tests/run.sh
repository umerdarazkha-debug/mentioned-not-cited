#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
PY="uv run --python 3.12 scripts/mnc.py"
F=tests/fixtures
fail=0
python3 tests/build_fixtures.py || exit 1
has() { if grep -qF -- "$3" <<<"$2"; then echo "ok   $1"; else echo "FAIL $1: missing '$3'"; fail=1; fi; }
not() { if grep -qF -- "$3" <<<"$2"; then echo "FAIL $1: should not contain '$3'"; fail=1; else echo "ok   $1"; fi; }

out=$($PY --answers $F/answers.csv --brand $F/brand.json --logs $F/access.log --logs $F/cloudflare.ndjson)
# Hand-derived from tests/build_fixtures.py
has chatgpt-rates "$out" "| chatgpt | 4 | 3 | 2 | 75% | 50% | 1 |"
has perplexity-rates "$out" "| perplexity | 4 | 3 | 1 | 75% | 25% | 2 |"
has all-rates "$out" "| All | 8 | 6 | 3 | 75% | 38% | 3 |"
# 'Acmeville' must not count as a mention; subdomain blog.acme-example.com must count as cited;
# notacme-example.com must not count as cited.
has gap-count "$out" "mentioned but not cited (3)"
has gap1 "$out" "| chatgpt | cheap analytics | reviewsite.example.org/best-tools; rivalytics.example.net/pricing | reviewsite.example.org (third party); rivalytics.example.net (competitor: Rivalytics) |"
has gap2 "$out" "| perplexity | best analytics tool | reviewsite.example.org/best-tools; forum.example.com/thread |"
has gap3 "$out" "| perplexity | analytics for startups | (no citations) | - |"
not startups-chatgpt-not-gap "$out" "| chatgpt | analytics for startups |"
has rank1 "$out" "| 1 | reviewsite.example.org/best-tools | 3 | chatgpt, perplexity | third party |"
has rank-lookalike "$out" "| 3 | notacme-example.com/x | 1 | perplexity | third party |"
has competitor "$out" "| 5 | rivalytics.example.net/pricing | 1 | chatgpt | competitor: Rivalytics |"
has comp-mentions "$out" "Rivalytics: chatgpt 1, perplexity 1"
# logs: bot totals (NotGPTBot must not count; 404s count in totals but not in page list)
has gptbot "$out" "| GPTBot | 10 |"
has claudebot "$out" "| ClaudeBot | 6 |"
has claudeuser "$out" "| Claude-User | 4 |"
has oai "$out" "| OAI-SearchBot | 2 |"
has googleext "$out" "Google-Extended is a robots.txt token"
has never-count "$out" "but no answer cited (3)"
has never1 "$out" "| /docs/setup | 5 | ClaudeBot 3, PerplexityBot 2 |"
has never2 "$out" "| /features | 4 | Claude-User 4 |"
has never3 "$out" "| /changelog | 3 | ClaudeBot 3 |"
not cited-page-excluded "$out" "| /blog/guide |"
not pricing-excluded "$out" "| /pricing | "
not old-below-threshold "$out" "| /old-page |"
not robots-excluded "$out" "| /robots.txt |"

out=$($PY --answers $F/answers.csv --brand $F/brand.json --logs $F/access.log --min-hits 5)
has minhits "$out" "but no answer cited (1)"

$PY --answers $F/bad.csv --brand $F/brand.json >/dev/null 2>&1 && { echo "FAIL bad-csv accepted"; fail=1; } || echo "ok   bad-csv rejected"
jq -e '[.bots[] | .source_url | startswith("https://")] | all' references/ai-bots.json >/dev/null && echo "ok   bots-sourced" || { echo "FAIL bots-sourced"; fail=1; }

[ $fail -eq 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
