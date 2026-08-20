"""axs-client — minimal client for AXS, the compact agent language of the AX Protocol.

fetch lexicon → compose → execute → decode. Zero dependencies, Python 3.9+.
Spec: https://rainz.ai/spec/ax-1.0/ · https://github.com/adirnur/ax-protocol
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Union

__version__ = "0.1.0"
__all__ = ["AXSClient", "Answer", "compose", "decode", "quote", "unquote"]

DEFAULT_ORIGIN = "https://rainz.ai"
_NEEDS_QUOTES = re.compile(r'[\s|"\\]')


def quote(v: Any) -> str:
    """Quote a value per AXS rules (whitespace, |, ", \\ force double quotes)."""
    v = str(v)
    if _NEEDS_QUOTES.search(v):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return v


def unquote(v: str) -> str:
    """Reverse of quote()."""
    if len(v) >= 2 and v.startswith('"') and v.endswith('"'):
        return re.sub(r'\\(["\\])', r"\1", v[1:-1])
    return v


def compose(head: str, pairs: Optional[dict] = None, **kw: Any) -> str:
    """Compose one AXS sentence.

    compose('q.svc.pr', n=3)             -> 'ax1 q.svc.pr n=3'
    compose('$ get.ofr.pr', i='of-1')    -> 'ax1 $ get.ofr.pr i=of-1'
    """
    parts = ["ax1", head]
    merged = dict(pairs or {})
    merged.update(kw)
    for k, v in merged.items():
        if v is None:
            continue
        parts.append(f"{k}={quote(v)}")
    return " ".join(parts)


def _split_top(s: str, sep: str) -> list:
    """Split on sep, ignoring separators inside double quotes."""
    out, cur, q, i = [], [], False, 0
    while i < len(s):
        c = s[i]
        if q:
            cur.append(c)
            if c == "\\" and i + 1 < len(s):
                i += 1
                cur.append(s[i])
            elif c == '"':
                q = False
        elif c == '"':
            q = True
            cur.append(c)
        elif c == sep:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        i += 1
    out.append("".join(cur))
    return out


def _parse_pairs(tokens: Iterable[str]):
    pairs, words = {}, []
    for t in tokens:
        eq = t.find("=")
        if eq > 0:
            pairs[t[:eq]] = unquote(t[eq + 1 :])
        elif t:
            words.append(t)
    return pairs, words


@dataclass
class Answer:
    """One decoded AXS answer.

    status: 'ok' | 'err' | 'rep?'
    head:   parsed head pairs — op, cov, cb, nx, nxu, nxx, code, d, ...
    rows:   '=' tuples, each a dict of field code -> value
    hints:  '+' rows, each a dict with 'name' plus its pairs
    raw:    this answer verbatim
    """

    status: str = ""
    head: dict = field(default_factory=dict)
    rows: list = field(default_factory=list)
    hints: list = field(default_factory=list)
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def cov(self) -> float:
        try:
            return float(self.head.get("cov", 0))
        except ValueError:
            return 0.0


def decode(text: str) -> list:
    """Decode a raw AXS response into a list of Answers (a stela of N
    sentences yields N answers, separated by `--` on the wire)."""
    return [_decode_one(b) for b in re.split(r"\r?\n--\r?\n", str(text))]


def _decode_one(block: str) -> Answer:
    lines = [l for l in block.splitlines() if l.strip()]
    answer = Answer(raw=block)
    if not lines:
        return answer

    tokens = [t for t in _split_top(lines[0], " ") if t]
    pairs, words = _parse_pairs(tokens[1:])  # tokens[0] == 'ax1'
    answer.status = words[0] if words else ""
    answer.head = pairs

    for line in lines[1:]:
        if line.startswith("="):
            row = {}
            for fld in _split_top(line[1:], "|"):
                colon = fld.find(":")  # split at the FIRST ':'
                if colon > 0:
                    row[fld[:colon]] = unquote(fld[colon + 1 :])
            answer.rows.append(row)
        elif line.startswith("+"):
            hp, hw = _parse_pairs([t for t in _split_top(line[1:], " ") if t])
            hint = {"name": hw[0] if hw else ""}
            hint.update(hp)
            answer.hints.append(hint)
    return answer


class AXSClient:
    """AXS client. One origin, three verbs of API::

        ax = AXSClient()                      # rainz.ai
        ax = AXSClient('https://example.com') # any site running the AX Protocol plugin

        ax.lexicon()                          # the living vocabulary (dict)
        ax.ask('q.svc.pr', n=3)               # one sentence -> one decoded Answer
        ax.stela(['q.cat n=2', 'q.new'])      # N sentences, one round trip
        ax.lead(name=..., email=..., message=...)  # the only side-effectful verb
    """

    def __init__(self, origin: str = DEFAULT_ORIGIN, timeout: float = 15.0):
        self.origin = origin.rstrip("/")
        self.timeout = timeout

    @property
    def endpoint(self) -> str:
        return self.origin + "/wp-json/ax/v1/x"

    def _get(self, url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": f"axs-client/{__version__} (python)"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read().decode("utf-8")

    def lexicon(self) -> dict:
        """The hub's living lexicon: verbs, nouns, qualifiers, scripts, desire paths."""
        return json.loads(self._get(self.origin + "/wp-json/rainz-axs/v1/lexicon"))

    def raw(self, line: str) -> str:
        """Send one raw AXS line (GET), return the raw text reply."""
        return self._get(self.endpoint + "?s=" + urllib.parse.quote(line, safe=""))

    def ask(self, head: str, pairs: Optional[dict] = None, **kw: Any) -> Answer:
        """Compose one sentence, execute it, decode the single answer."""
        return decode(self.raw(compose(head, pairs, **kw)))[0]

    def stela(self, sentences: Iterable[Union[str, tuple]]) -> list:
        """Batch read sentences (a "stela"): N sentences, one POST, N answers."""
        lines = []
        for s in sentences:
            if isinstance(s, str):
                lines.append(s if s.startswith("ax1") else "ax1 " + s)
            else:
                lines.append(compose(s[0], s[1] if len(s) > 1 else None))
        req = urllib.request.Request(
            self.endpoint,
            data="\n".join(lines).encode("utf-8"),
            headers={
                "Content-Type": "text/plain; charset=utf-8",
                "User-Agent": f"axs-client/{__version__} (python)",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return decode(r.read().decode("utf-8"))

    def lead(
        self,
        name: str,
        email: str,
        message: str,
        acting_for: Optional[str] = None,
        key: Optional[str] = None,
    ) -> Answer:
        """Submit an enquiry — do.lead, the only verb with a side effect.
        Pass `key` for idempotency (safe retries)."""
        return decode(
            self.raw(compose("do.lead", nm=name, em=email, ms=message, fo=acting_for, k=key))
        )[0]
