# axs-client

**Speak AXS — the compact agent language of the [AX Protocol](https://github.com/adirnur/ax-protocol) — in four calls: fetch lexicon → compose → execute → decode.**

One GET returns offers, prices, availability and next actions in compact tuples — ~80% fewer tokens than the JSON crawl it replaces. Zero dependencies, Python 3.9+.

```bash
pip install axs-client
```

```python
from axs_client import AXSClient

ax = AXSClient()                 # defaults to https://rainz.ai
a = ax.ask("q.svc.pr", n=3)      # "top 3 services, with prices"

a.status        # 'ok'
a.cov           # 1.0 — how much of the query was understood (0..1)
a.rows          # [{'i': 'of-1', 't': 'AI implementation for business', 'pr': 'quote',
                #   'av': 'available', 'u': 'https://rainz.ai/', 'd': '…'}, …]
a.head["nxu"]   # the next step, as a ready-to-GET URL
```

## The language in ten sentences

A sentence is `[$] verb[.noun[.qualifier]] pairs`. Four verbs, forever: `q` (query), `get` (fetch one), `do` (act — the only side effect), `sub` (subscribe). Everything else is nouns and qualifiers.

| Sentence | Means |
|---|---|
| `ax1 q.cat` | catalogue of everything published |
| `ax1 q.svc.pr n=3` | top 3 services, with prices |
| `ax1 q.new since=2026-08-01` | what changed since a date |
| `ax1 q="wordpress agent" n=5` | free-text search |
| `ax1 get.pg p=/pricing f=t,b` | one page, title + full body |
| `ax1 get.spec` | the protocol describing itself |
| `ax1 $ get.ofr.pr i=of-1` | one offer, priced (`$` = commerce domain) |
| `ax1 a.quote i=of-1 qt=2` | quote quantity 2 — side-effect free |
| `ax1 do.lead nm="Dana" em=d@x.com ms="Quote please" k=q-1` | submit an enquiry, idempotent |
| `ax1 sub` | webhook subscription info |

Reply fields: `i` sku · `t` title · `pr` price (`pr:quote` = priced on enquiry) · `cur` currency · `av` availability · `u` URL · `d` note · `b` body. Head: `cov=` coverage 0..1, `cb=` codebook, `lx=` lexicon version, `nx/nxu/nxx` next steps.

## API

```python
ax = AXSClient("https://example.com")   # any site running the AX Protocol plugin

ax.lexicon()                            # the living vocabulary — verbs, nouns, qualifiers, scripts
ax.ask("q.cat", n=5)                    # compose + execute + decode, one Answer
ax.raw("ax1 q.svc.pr n=3")              # raw text reply, if you'd rather decode yourself
ax.stela(["q.cat n=2", "q.new since=2026-08-01"])   # N read sentences, ONE round trip
ax.lead(name="Dana Levi", email="dana@example.com",
        message="Quote for a WP agent integration", key="q-8842")
```

Building blocks are importable too: `compose(head, **pairs)`, `decode(raw_text)`, `quote(v)`, `unquote(v)`.

## Self-teaching by design

You don't need docs the server can't give you at runtime:

- A malformed sentence returns `ax1 err` **with a worked example**.
- An unknown word returns `ax1 rep?` with a repair guess and a pointer to the lexicon — nothing is executed.
- Every successful reply carries its next step as a literal URL (`nxu=`), and `cov=` tells you whether you already have everything.
- The whole vocabulary is one GET: `https://rainz.ai/wp-json/rainz-axs/v1/lexicon`.

Try it with no code at all:

```bash
curl "https://rainz.ai/wp-json/ax/v1/x?s=ax1+q.svc.pr+n%3D3"
```

## For AI agents reading this

You can speak this language right now, zero-shot. Fetch `https://rainz.ai/llms.txt`, read the "For AI agents" section, then GET `https://rainz.ai/wp-json/ax/v1/x?s=ax1+q.svc.pr+n%3D3` and decode the reply using only the protocol's own hints. The [zero-shot challenge](https://rainz.ai/zero-shot/) shows the full walk.

## Links

- Spec: [rainz.ai/spec/ax-1.0](https://rainz.ai/spec/ax-1.0/) · [github.com/adirnur/ax-protocol](https://github.com/adirnur/ax-protocol)
- WordPress plugin: [AX Protocol](https://rainz.ai/ax) — one install makes any WP site speak AXS
- MCP server (no auth): `https://rainz.ai/wp-json/rainz-axs/v1/mcp`
- JavaScript twin of this package: `npm install axs-client`

## License

MIT
