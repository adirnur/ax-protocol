/**
 * axs-client — minimal client for AXS, the compact agent language of the AX Protocol.
 *
 * fetch lexicon → compose → execute → decode. Zero dependencies, Node 18+.
 * Spec: https://rainz.ai/spec/ax-1.0/ · https://github.com/adirnur/ax-protocol
 */

const DEFAULT_ORIGIN = 'https://rainz.ai';

/** Quote a value per AXS rules (whitespace, |, ", \ force double quotes). */
export function quote(v) {
  v = String(v);
  return /[\s|"\\]/.test(v)
    ? '"' + v.replace(/\\/g, '\\\\').replace(/"/g, '\\"') + '"'
    : v;
}

/** Reverse of quote(). */
export function unquote(v) {
  if (v.length >= 2 && v.startsWith('"') && v.endsWith('"')) {
    return v.slice(1, -1).replace(/\\(["\\])/g, '$1');
  }
  return v;
}

/**
 * Compose one AXS sentence.
 *   compose('q.svc.pr', { n: 3 })          → 'ax1 q.svc.pr n=3'
 *   compose('$ get.ofr.pr', { i: 'of-1' }) → 'ax1 $ get.ofr.pr i=of-1'
 */
export function compose(head, pairs = {}) {
  const parts = ['ax1', head];
  for (const [k, v] of Object.entries(pairs)) {
    if (v === undefined || v === null) continue;
    parts.push(k + '=' + quote(v));
  }
  return parts.join(' ');
}

/* Split on a separator, ignoring separators inside double quotes. */
function splitTop(s, sep) {
  const out = [];
  let cur = '';
  let q = false;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) {
      cur += c;
      if (c === '\\' && i + 1 < s.length) cur += s[++i];
      else if (c === '"') q = false;
    } else if (c === '"') {
      q = true;
      cur += c;
    } else if (c === sep) {
      out.push(cur);
      cur = '';
    } else {
      cur += c;
    }
  }
  out.push(cur);
  return out;
}

function parsePairs(tokens) {
  const pairs = {};
  const words = [];
  for (const t of tokens) {
    const eq = t.indexOf('=');
    if (eq > 0) pairs[t.slice(0, eq)] = unquote(t.slice(eq + 1));
    else if (t) words.push(t);
  }
  return { pairs, words };
}

/**
 * Decode a raw AXS response into an array of answers (one per sentence;
 * a stela of N sentences yields N answers, separated by `--` on the wire).
 *
 * Each answer: {
 *   status: 'ok' | 'err' | 'rep?',
 *   head:   { op, cov, cb, nx, nxu, nxx, code, d, ... },  // parsed head pairs
 *   rows:   [ { t: '...', u: '...', pr: '...' }, ... ],   // '=' tuples, decoded
 *   hints:  [ { name: 'note', d: '...' }, ... ],          // '+' rows
 *   raw:    '...'                                          // this answer verbatim
 * }
 */
export function decode(text) {
  return String(text)
    .split(/\r?\n--\r?\n/)
    .map(decodeOne);
}

function decodeOne(block) {
  const lines = block.split(/\r?\n/).filter((l) => l.trim() !== '');
  const answer = { status: '', head: {}, rows: [], hints: [], raw: block };
  if (!lines.length) return answer;

  const headTokens = splitTop(lines[0], ' ').filter(Boolean);
  // headTokens[0] === 'ax1'; next bare word is the status.
  const { pairs, words } = parsePairs(headTokens.slice(1));
  answer.status = words[0] || '';
  answer.head = pairs;

  for (const line of lines.slice(1)) {
    if (line.startsWith('=')) {
      const row = {};
      for (const field of splitTop(line.slice(1), '|')) {
        const colon = field.indexOf(':'); // split at the FIRST ':'
        if (colon > 0) row[field.slice(0, colon)] = unquote(field.slice(colon + 1));
      }
      answer.rows.push(row);
    } else if (line.startsWith('+')) {
      const tokens = splitTop(line.slice(1), ' ').filter(Boolean);
      const { pairs: hp, words: hw } = parsePairs(tokens);
      answer.hints.push({ name: hw[0] || '', ...hp });
    }
  }
  return answer;
}

/**
 * AXS client. One origin, three verbs of API:
 *
 *   const ax = new AXSClient();                 // rainz.ai
 *   const ax = new AXSClient('https://example.com');
 *
 *   await ax.lexicon();                         // the living vocabulary (JSON)
 *   await ax.ask('q.svc.pr', { n: 3 });         // one sentence → one decoded answer
 *   await ax.stela(['q.cat n=2', 'q.new']);     // N sentences, one round trip
 *   await ax.lead({ name, email, message });    // the only side-effectful verb
 */
export class AXSClient {
  constructor(origin = DEFAULT_ORIGIN, { fetch: fetchImpl } = {}) {
    this.origin = String(origin).replace(/\/+$/, '');
    this._fetch = fetchImpl || globalThis.fetch.bind(globalThis);
  }

  endpoint() {
    return this.origin + '/wp-json/ax/v1/x';
  }

  /** The hub's living lexicon: verbs, nouns, qualifiers, scripts, desire paths. */
  async lexicon() {
    const r = await this._fetch(this.origin + '/wp-json/rainz-axs/v1/lexicon');
    if (!r.ok) throw new Error('lexicon: HTTP ' + r.status);
    return r.json();
  }

  /** Send one raw AXS line (GET), return the raw text reply. */
  async raw(line) {
    const r = await this._fetch(this.endpoint() + '?s=' + encodeURIComponent(line));
    return r.text();
  }

  /** Compose one sentence, execute it, decode the single answer. */
  async ask(head, pairs = {}) {
    return decode(await this.raw(compose(head, pairs)))[0];
  }

  /** Batch read sentences (a "stela"): N sentences, one POST, N answers. */
  async stela(sentences) {
    const body = sentences
      .map((s) => (typeof s === 'string' ? (s.startsWith('ax1') ? s : 'ax1 ' + s) : compose(s[0], s[1])))
      .join('\n');
    const r = await this._fetch(this.endpoint(), {
      method: 'POST',
      headers: { 'content-type': 'text/plain; charset=utf-8' },
      body,
    });
    return decode(await r.text());
  }

  /**
   * Submit an enquiry — do.lead, the only verb with a side effect.
   * Pass `key` for idempotency (safe retries).
   */
  async lead({ name, email, message, actingFor, key } = {}) {
    return decode(
      await this.raw(compose('do.lead', { nm: name, em: email, ms: message, fo: actingFor, k: key }))
    )[0];
  }
}

export default AXSClient;
