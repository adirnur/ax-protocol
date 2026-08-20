# AX Protocol / AXS — the agent layer for the open web

**One GET. Offers, prices, availability and next actions. ~80% fewer tokens than the JSON crawl it replaces.**

```
curl "https://rainz.ai/wp-json/ax/v1/x?s=ax1+q.svc.pr+n%3D3"
```

```
ax1 ok op=o n=3 cov=1 cb=2 nx="a.quote i=<sku>; a.lead @ POST https://rainz.ai/wp-json/ax/v1/intent" nxu=… nxx=…
=i:of-1|t:"AI implementation for business"|pr:quote|av:available|u:https://rainz.ai/|d:"Custom-scoped engagement; quote on enquiry"
=i:of-2|t:"Business stability architecture"|pr:quote|av:available|u:https://rainz.ai/|d:"Revenue, operations and data connected into one system"
=i:of-3|t:"UX and content strategy"|pr:quote|av:available|u:https://rainz.ai/|d:"Digital strategy, user experience and content"
```

That reply is live. Every line above came from one HTTP round trip, and it carries its own next steps: `nx=` (actions), `nxu=` (next query as a ready URL), `nxx=` (a referral to a verified sibling site in the network).

## Why

An agent interaction with a website today costs 4–6 round trips and thousands of JSON tokens, most of them repeated keys. AXS is declarative: the caller states intent, the origin resolves it server-side and answers in compact tuples with a shared codebook. Every reply reports `cov=` (how much of the query was understood), so the agent knows immediately whether it needs another round trip.

## The zero-shot property

The protocol teaches itself in-band:

- `https://rainz.ai/llms.txt` ends with a **For AI agents** section: endpoint, a literal Try URL, the reply format, the field hints.
- A malformed sentence returns `ax1 err` **with a worked example**.
- Every successful reply carries the next step as a copy-paste URL.

An agent that has never seen AXS learns it in one conversation. Try it: [the zero-shot challenge](https://rainz.ai/zero-shot/).

## Speak it

| Sentence | Means |
|---|---|
| `ax1 q.svc.pr n=3` | top 3 services with prices |
| `ax1 a.quote i=of-1 qt=2` | quote offer of-1, quantity 2 |
| `ax1 sub` | webhook subscription info |
| `ax1 q.new since=2026-08-01` | what changed since a date |

Reply fields: `i` sku, `t` title, `pr` price (`pr:quote` = priced on enquiry), `cur` currency, `av` availability, `u` URL, `d` note. Header: `cov=` coverage 0..1, `cb=` codebook version.

## Get it

- **WordPress plugin** — [AX Protocol](https://rainz.ai/ax). One install: llms.txt, `/.well-known/ax.json`, JSON page twins, the AXS endpoint, agent detection and a conformance self-test. Humans and search engines see the site exactly as before.
- **MCP server** (whole network, Streamable HTTP, no auth): `https://rainz.ai/wp-json/rainz-axs/v1/mcp` — tools `ax_network_sites`, `ax_offers`, `ax_query`.
- **Spec**: [`AXS-1.0.md`](AXS-1.0.md) in this repo, or [rainz.ai/spec/ax-1.0](https://rainz.ai/spec/ax-1.0/).

## Status

Live on a 15-site network. Plugin submitted to the WordPress.org directory. Spec: Draft 1, feedback welcome — open an issue.

## License

Spec: CC BY-SA 4.0. Plugin: GPL-2.0-or-later.

