# AXS-1.0 — AX Shorthand

**A compact, declarative interchange language between user agents and site agents.**
Extension to AX-1.0 (proposed §13). Status: Draft 1. Author: Rainz.ai. 2026-07-30.

---

## 1. Why

An agent interaction with an AX origin today costs four to six HTTP round trips
(manifest → catalogue → page → action) and thousands of JSON tokens, most of
them repeated keys and structural noise. For an agent that pays per token and
per second, that cost decides which sites get used.

AXS applies the principle behind scenario-description languages such as
Foretellix's M-SDL: **the caller declares intent and constraints, not steps.**
The origin resolves the whole intent server-side and answers in compact tuples.
Three mechanisms carry the saving:

1. **One line in, one round trip.** A single declarative request replaces the
   chain of REST calls.
2. **A shared codebook.** Both sides speak in short codes published in the
   manifest (the same trick HPACK plays for HTTP/2 headers). Keys are never
   repeated per row; a codebook change bumps a version instead of breaking
   old agents.
3. **Measurable coverage.** Every response reports `cov` (0..1) — how much of
   the request was satisfied — so the agent knows immediately whether it needs
   another round trip or already has everything.

Measured on a typical "find a service page and read it" flow: **~75–85% fewer
tokens and 3–5 fewer round trips** than the equivalent JSON REST sequence.

## 2. Transport

- Endpoint: `POST` or `GET` `{rest}/ax/v1/x`
  - `GET  …/x?s=<urlencoded AXS line>`
  - `POST …/x` with the raw AXS line as a `text/plain` body
- Response: `text/plain; charset=utf-8`, header `AX-Compact: AXS-1.0; cb=<codebook version>`
- Discovery: the manifest (`/.well-known/ax.json`) carries an `x_compact`
  block: `spec`, `endpoint`, `codebook_version`, `codebook`, `example`.
  (`x_`-namespaced so AX-1.0 validators ignore it safely; becomes `compact`
  when AX-1.1 lands.)

## 3. Request grammar

```
line    := "ax1" SP [op] *(SP pair)
op      := "m" | "c" | "s" | "p" | "a.lead"
pair    := key "=" value
value   := quoted | bareword
quoted  := DQUOTE *(escaped char) DQUOTE     ; \" and \\ escapes
```

If `op` is omitted it is inferred: `q=` present → `s`; `p=` present → `p`;
otherwise `m`.

### Operations

| op | meaning | required | optional |
|---|---|---|---|
| `m` | site/org summary | — | `f` |
| `c` | catalogue | — | `n`, `f` |
| `s` | search | `q` | `n`, `f`, `l` |
| `p` | page twin | `p` (id or path) | `f`, `x` |
| `a.lead` | submit an enquiry | `nm`, `em`, `ms` | `fo`, `k` |

### Request keys (codebook v1)

`q` query text · `p` page id or path · `f` comma-list of response field codes ·
`n` max results (1–20) · `l` language code · `x` include full body (`1`) ·
`k` idempotency key · `nm` name · `em` email · `ms` message · `fo` acting-for.

## 4. Response grammar

```
response := head *(LF row)
head     := "ax1" SP ("ok" / "err") *(SP pair)
row      := ("=" tuple) / ("+" hint)
tuple    := field *("|" field)
field    := code ":" value
```

- Head always carries `op`, `cov` and `cb` (codebook version) on success, or
  `code` and `d` on error.
- `=` rows are result tuples. `+` rows are hints (next step, CTA, reference).
- Values containing whitespace, `|`, `"` or `\` are double-quoted with
  C-style escapes. The consumer splits each field at the **first** `:`.

### Response field codes (codebook v1)

`t` title · `u` url · `d` description/summary · `y` type · `dt` updated ·
`pb` published · `au` author · `b` full body · `o` organisation ·
`e` email · `ph` phone · `r` receipt reference · `st` status ·
`cov` coverage · `l` language(s).

## 5. Coverage (`cov`)

- `s`: results returned ÷ results requested (capped at 1).
- `p`: fields resolved ÷ fields requested.
- `m`, `c`: `1` (self-describing).
- `a.lead`: `1` on receipt — a receipt is total or absent.

An agent SHOULD treat `cov < 1` as a signal to widen the query or fall back to
the verbose REST surface, never as silent partial success.

## 6. Actions

`a.lead` inherits every guarantee of the AX-1.0 `/intent` action unchanged:
same rate limit (§12.2), same idempotency semantics via `k` (§8.4), same
human-readable receipt (§9.1), same `creates_record`-only side effect (§8.2).
AXS is a syntax, not a second policy surface.

## 7. Examples

Search, three results, titles and URLs only:

```
→ ax1 q="AI agents package pricing" n=3 f=t,u
← ax1 ok op=s n=2 cov=0.67 cb=1
  =t:"AI Agent Development"|u:https://rainz.ai/services/ai-agents
  =t:"Pricing"|u:https://rainz.ai/pricing
```

Read one page in full:

```
→ ax1 p=/pricing f=t,b
← ax1 ok op=p cov=1 cb=1
  =t:Pricing|b:"Full plain-text body…"
```

Submit an enquiry, idempotent:

```
→ ax1 a.lead nm="Dana Levi" em=dana@example.com ms="Quote for a WP agent integration" k=q-8842
← ax1 ok op=a.lead cov=1 cb=1
  =r:AX-K3J9Q2MF|st:received|dt:2026-07-30T10:41:00+00:00|d:"An enquiry from Dana Levi…"|e:hello@rainz.ai
```

Error:

```
→ ax1 s n=3
← ax1 err code=missing_q d="s needs q=..."
```

## 8. Conformance (proposed §13 checks)

- **13.1** The origin answers a single-line AXS request at the declared endpoint.
- **13.2** The codebook is published, versioned, in the manifest.
- **13.3** Every response reports its own coverage.

## 9. Security

AXS adds no new capability: `m/c/s/p` expose only what the JSON surface already
exposes, and `a.lead` delegates to the existing action including its permission
gate and rate limit. The request line is length-capped (2000 chars) and fully
sanitised before resolution.

## 10. Codebook version 2 — the commerce codes

Codebook v2 (shipped with AX Protocol 1.2.0) registers two operations and
seven codes on top of v1. A v1 agent is unaffected: unknown ops fail closed
with `bad_op`, and unknown response codes resolve through the published
codebook, which is the mechanism doing its job.

New operations:

- **`o`** — offers: what is for sale, priced. Tuples of `i` (offer id), `t`,
  `pr` (unit price), `cur` (ISO 4217), `av` (availability), `u`, optional `d`.
- **`a.quote`** — price one offer at a quantity: `ax1 a.quote i=of-1 qt=2`.
  Side-effect free by definition: nothing is reserved, no record is created.
  Answers with `qt`, `pr`, `tt` (total), `cur`, `av`, and `rd` (returns
  window in days) when the origin declares one. Inferred when `i=` is present
  without an explicit op.

New request keys: `i` (offer id), `qt` (quantity).
New response codes: `i`, `pr`, `cur`, `av`, `qt`, `tt`, `rd`.

```
→ ax1 a.quote i=of-1 qt=2
← ax1 ok op=a.quote cov=1 cb=2
← =i:of-1|t:"AI readiness audit"|qt:2|pr:4900|tt:9800|cur:ILS|av:available|rd:14
← +note d="Indicative and side-effect free. Nothing was reserved or recorded."
```

An origin with nothing to sell publishes no `commerce` block and answers
`o` with an empty list; its manifest is byte-identical to a v1 manifest
except for the codebook version. The commerce layer is therefore strictly
additive, like everything else in this specification.
