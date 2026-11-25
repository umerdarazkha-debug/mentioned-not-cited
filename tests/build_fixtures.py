#!/usr/bin/env python3
import csv, json, os
F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
os.makedirs(F, exist_ok=True)
json.dump({"brand_names": ["Acme Analytics", "Acme", "AcmeAnalytics"], "own_domains": ["acme-example.com"],
           "competitors": [{"name": "Rivalytics", "domains": ["rivalytics.example.net"]}]},
          open(os.path.join(F, "brand.json"), "w"), indent=2)
A = [
 ("chatgpt", "best analytics tool", "Acme Analytics is a solid pick.", "https://acme-example.com/blog/guide|https://other.example.org/review"),
 ("chatgpt", "cheap analytics", "Acme is cheap. Rivalytics costs more.", "https://reviewsite.example.org/best-tools|https://rivalytics.example.net/pricing"),
 ("chatgpt", "analytics for startups", "Try the tools in Acmeville.", "https://www.reviewsite.example.org/best-tools/?utm_source=x"),
 ("chatgpt", "privacy analytics", "AcmeAnalytics is privacy friendly.", "https://blog.acme-example.com/post"),
 ("perplexity", "best analytics tool", "Acme leads. Rivalytics is second.", "https://reviewsite.example.org/best-tools?utm_source=y|https://forum.example.com/thread"),
 ("perplexity", "cheap analytics", "Several tools exist.", "https://notacme-example.com/x"),
 ("perplexity", "analytics for startups", "Acme works well for startups.", ""),
 ("perplexity", "analytics pricing", "acme lists its price on its site.", "https://acme-example.com/pricing"),
]
with open(os.path.join(F, "answers.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["engine", "prompt", "answer_text", "cited_urls"]); w.writerows(A)
UA = {"gpt": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; GPTBot/1.4; +https://openai.com/gptbot",
      "cgu": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot",
      "oai": "Mozilla/5.0 (X11) compatible; OAI-SearchBot/1.4; +https://openai.com/searchbot",
      "cb": "Mozilla/5.0 (compatible; ClaudeBot/1.0)", "cu": "Claude-User/1.0",
      "pb": "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
      "fake": "Mozilla/5.0 (compatible; XGPTBot/1.0)", "human": "Mozilla/5.0 (Macintosh) Chrome/120.0 Safari/537.36",
      "g": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"}
lines = []
def hit(path, ua, n, status=200):
    for _ in range(n):
        lines.append('203.0.113.7 - - [10/Nov/2026:10:00:00 +0000] "GET %s HTTP/1.1" %d 512 "-" "%s"' % (path, status, UA[ua]))
hit("/blog/guide", "gpt", 2); hit("/blog/guide?utm=1", "cgu", 1)
hit("/docs/setup", "cb", 3); hit("/docs/setup", "pb", 2); hit("/docs/setup", "human", 10); hit("/docs/setup", "fake", 3)
hit("/docs/setup", "gpt", 2, 404)
hit("/pricing", "oai", 2); hit("/old-page", "gpt", 1); hit("/features/", "cu", 4); hit("/features", "g", 6)
hit("/robots.txt", "gpt", 5)
open(os.path.join(F, "access.log"), "w").write("\n".join(lines) + "\n")
cf = []
for _ in range(3):
    cf.append(json.dumps({"ClientIP": "198.51.100.9", "ClientRequestHost": "example.com", "ClientRequestMethod": "GET", "ClientRequestURI": "/changelog?x=1",
                          "ClientRequestUserAgent": UA["cb"], "EdgeResponseStatus": 200, "EdgeStartTimestamp": "2026-11-10T10:00:00Z"}))
open(os.path.join(F, "cloudflare.ndjson"), "w").write("\n".join(cf) + "\n")
with open(os.path.join(F, "bad.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["engine", "prompt"]); w.writerow(["chatgpt", "x"])
