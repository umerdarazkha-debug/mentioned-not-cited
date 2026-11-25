#!/usr/bin/env python3
"""Mentioned vs cited: compare brand mentions with citations in AI answers.

Usage:
  uv run --python 3.12 scripts/mnc.py --answers answers.csv --brand brand.json
      [--logs access.log --logs cf.ndjson] [--min-hits 3] [--top 20] [--out report.md] [--json out.json]
"""
import argparse, csv, json, os, re, sys
from collections import Counter, defaultdict
from urllib.parse import urlparse, parse_qsl, urlencode

HERE = os.path.dirname(os.path.abspath(__file__))
ALIASES = {
    "engine": ["engine", "platform", "model", "assistant"],
    "prompt": ["prompt", "query", "question"],
    "answer": ["answer_text", "answer", "response", "text"],
    "cited": ["cited_urls", "citations", "sources", "cited", "urls"],
}
TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref$|ref_src$|srsltid)", re.I)
ASSET = re.compile(r"\.(css|js|mjs|map|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|xml|txt|json|pdf|mp4|webm)$", re.I)


def norm(h):
    return h.strip().lstrip("﻿").lower()


def split_urls(s):
    return [u.strip() for u in re.split(r"[|\n]", s or "") if u.strip()]


def host_and_key(u):
    u = u.strip()
    if "://" not in u:
        u = "https://" + u
    p = urlparse(u)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    return host, host + path


def host_matches(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def alias_re(names):
    parts = [re.escape(n) for n in sorted(names, key=len, reverse=True) if n.strip()]
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(parts) + r")(?![A-Za-z0-9])", re.I)


def load_answers(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        nh = {norm(h): h for h in rd.fieldnames or []}
        m = {}
        for k, names in ALIASES.items():
            m[k] = next((nh[n] for n in names if n in nh), None)
        miss = [k for k in ("engine", "prompt", "answer", "cited") if not m[k]]
        if miss:
            sys.exit("ERROR: answers CSV is missing columns %s. Need engine, prompt, answer_text, cited_urls (separated by |). Found: %s" % (miss, rd.fieldnames))
        return [dict(engine=r[m["engine"]].strip(), prompt=r[m["prompt"]].strip(), answer=r[m["answer"]], cited=split_urls(r[m["cited"]])) for r in rd]


COMBINED = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "(\S+) (\S+)[^"]*" (\d{3}) (\S+) "([^"]*)" "([^"]*)"')


def parse_logs(paths):
    """Yield (method, path, status, user_agent). Handles Apache/Nginx combined format and Cloudflare Logpush NDJSON."""
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("{"):
                    try:
                        j = json.loads(line)
                    except ValueError:
                        continue
                    uri = j.get("ClientRequestURI") or j.get("ClientRequestPath") or ""
                    yield (j.get("ClientRequestMethod", "GET"), uri, int(j.get("EdgeResponseStatus") or 0), j.get("ClientRequestUserAgent", ""))
                else:
                    m = COMBINED.match(line)
                    if m:
                        yield (m.group(3), m.group(4), int(m.group(5)), m.group(8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--answers", required=True)
    ap.add_argument("--brand", required=True)
    ap.add_argument("--logs", action="append", default=[])
    ap.add_argument("--bots", default=os.path.join(HERE, "..", "references", "ai-bots.json"))
    ap.add_argument("--min-hits", type=int, default=3)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out"); ap.add_argument("--json")
    a = ap.parse_args()

    B = json.load(open(a.brand))
    brand_re = alias_re(B["brand_names"])
    own = [d.lower() for d in B["own_domains"]]
    comps = B.get("competitors", [])
    comp_re = {c["name"]: alias_re(c.get("names") or [c["name"]]) for c in comps}
    rows = load_answers(a.answers)

    per = defaultdict(lambda: Counter())
    gaps, cited_counter, cited_engines, cited_prompts, cited_owner = [], Counter(), defaultdict(set), defaultdict(set), {}
    own_cited_paths = set()
    for r in rows:
        e = r["engine"]
        per[e]["answers"] += 1
        mentioned = bool(brand_re.search(r["answer"]))
        hosts = [host_and_key(u) for u in r["cited"]]
        cited = any(host_matches(h, own) for h, _ in hosts)
        per[e]["mentioned"] += mentioned
        per[e]["cited"] += cited
        per[e]["mentioned_not_cited"] += (mentioned and not cited)
        for cn, cre in comp_re.items():
            if cre.search(r["answer"]):
                per[e]["comp:" + cn] += 1
        seen = set()
        for h, k in hosts:
            if host_matches(h, own):
                own_cited_paths.add(k.split("/", 1)[1] if "/" in k else "")
                continue
            owner = next((c["name"] for c in comps if host_matches(h, [d.lower() for d in c.get("domains", [])])), None)
            cited_owner[k] = ("competitor: " + owner) if owner else "third party"
            if k not in seen:
                cited_counter[k] += 1
                cited_engines[k].add(e); cited_prompts[k].add(r["prompt"])
                seen.add(k)
        if mentioned and not cited:
            gaps.append(dict(engine=e, prompt=r["prompt"], winning=[k for _, k in hosts],
                             owners=[(h, cited_owner[k]) for h, k in hosts], answer=r["answer"]))

    ranking = sorted(cited_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    L = ["# Mentioned vs cited", "",
         "A mention is the brand name in the answer text. A citation is one of your own domains in the cited URLs. Answers analysed: %d." % len(rows), ""]
    L += ["## Mention rate vs citation rate by engine", "", "| Engine | Answers | Mentioned | Cited | Mention rate | Citation rate | Mentioned, not cited |", "|---|---|---|---|---|---|---|"]
    tot = Counter()
    for e in sorted(per):
        c = per[e]
        tot.update(c)
        L.append("| %s | %d | %d | %d | %.0f%% | %.0f%% | %d |" % (e, c["answers"], c["mentioned"], c["cited"], 100 * c["mentioned"] / c["answers"], 100 * c["cited"] / c["answers"], c["mentioned_not_cited"]))
    L.append("| All | %d | %d | %d | %.0f%% | %.0f%% | %d |" % (tot["answers"], tot["mentioned"], tot["cited"], 100 * tot["mentioned"] / max(1, tot["answers"]), 100 * tot["cited"] / max(1, tot["answers"]), tot["mentioned_not_cited"]))
    if comps:
        L += ["", "Competitor mentions: " + "; ".join("%s: %s" % (cn, ", ".join("%s %d" % (e, per[e]["comp:" + cn]) for e in sorted(per))) for cn in comp_re)]
    L += ["", "## Prompts where the brand is mentioned but not cited (%d)" % len(gaps), "",
          "| Engine | Prompt | URLs cited instead | Whose domains |", "|---|---|---|---|"]
    for g in gaps:
        L.append("| %s | %s | %s | %s |" % (g["engine"], g["prompt"], "; ".join(g["winning"]) or "(no citations)",
                                           "; ".join("%s (%s)" % o for o in g["owners"]) or "-"))
    L += ["", "## Pages cited most (not yours): outreach or better-page targets", "",
          "| Rank | URL | Answers citing it | Engines | Owner |", "|---|---|---|---|---|"]
    for i, (k, n) in enumerate(ranking[:a.top], 1):
        L.append("| %d | %s | %d | %s | %s |" % (i, k, n, ", ".join(sorted(cited_engines[k])), cited_owner[k]))

    bot_totals, page_hits = Counter(), defaultdict(Counter)
    log_summary = None
    if a.logs:
        bots = json.load(open(a.bots))
        pats = [(b["token"], re.compile(r"(?<![A-Za-z0-9])" + re.escape(b["token"]), re.I)) for b in bots["bots"]]
        for method, path, status, ua in parse_logs(a.logs):
            tok = next((t for t, p in pats if p.search(ua)), None)
            if not tok:
                continue
            bot_totals[tok] += 1
            pth = urlparse(path).path or "/"
            if len(pth) > 1:
                pth = pth.rstrip("/") or "/"
            if status == 200 and method in ("GET", "HEAD") and not ASSET.search(pth):
                page_hits[pth][tok] += 1
        L += ["", "## AI bot hits in your logs", "",
              "Matched on the user agent tokens in references/ai-bots.json (sources inside). Google-Extended is a robots.txt token with no user agent of its own, so it never shows in logs (https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers).", "",
              "| Bot | Hits |", "|---|---|"]
        for b in bots["bots"]:
            L.append("| %s | %d |" % (b["token"], bot_totals[b["token"]]))
        never = []
        for pth, c in page_hits.items():
            n = sum(c.values())
            if n >= a.min_hits and pth.lstrip("/") not in own_cited_paths:
                never.append((pth, n, c))
        never.sort(key=lambda x: (-x[1], x[0]))
        L += ["", "## Pages AI bots crawl often (%d or more successful hits) but no answer cited (%d)" % (a.min_hits, len(never)), "",
              "| Page | Bot hits | Bots |", "|---|---|---|"]
        for pth, n, c in never:
            L.append("| %s | %d | %s |" % (pth, n, ", ".join("%s %d" % kv for kv in c.most_common())))
        L.append("")
        L.append("Crawled is not the same as used. Training bots and user-triggered fetchers are mixed here, and your answer set is a sample.")
        log_summary = dict(bots=dict(bot_totals), never_cited=[dict(page=p, hits=n) for p, n, _ in never])
    L += ["", "## Suggested page changes", "",
          "Claude writes this section from the workflow in SKILL.md, one entry per gap above. Fetch the winning page and your page, compare, and say what to add, change or earn."]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        open(a.out, "w").write(text)
    if a.json:
        json.dump(dict(engines={e: dict(c) for e, c in per.items()}, gaps=[{k: v for k, v in g.items()} for g in gaps],
                       ranking=[dict(url=k, answers=n, owner=cited_owner[k]) for k, n in ranking], logs=log_summary), open(a.json, "w"), indent=2)


if __name__ == "__main__":
    main()
