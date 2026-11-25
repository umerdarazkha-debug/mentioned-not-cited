# mentioned-not-cited

AI answers often name your brand and link a review site or a competitor. This skill counts how often, shows which prompts, and lists the pages that win the citation.

## Inputs

- `answers.csv`: `engine, prompt, answer_text, cited_urls` (`|` separated). Column names `platform`, `question`, `response`, `citations`, `sources` are also accepted.
- `brand.json`: brand names, own domains, competitors.
- Optional logs: Apache or Nginx combined format, or Cloudflare Logpush JSON lines.

## Install

```bash
git clone https://github.com/umerdarazkha-debug/mentioned-not-cited ~/.claude/skills/mentioned-not-cited
```

Copy to `~/.claude/skills/mentioned-not-cited/`. Needs `uv`. No other dependencies.

## Test

`bash tests/run.sh`. Eight synthetic answers, two engines, exact rates, three gap rows, a lookalike domain and a lookalike bot name that must not count. Offline.

## Limits

Sample-based. Bot user agents were checked on 2026-11-26 against the vendor pages listed in `references/ai-bots.json`.

## License

MIT
