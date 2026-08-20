import assert from 'node:assert/strict';
import { compose, decode, quote, unquote, AXSClient } from './index.js';

// compose + quoting
assert.equal(compose('q.svc.pr', { n: 3 }), 'ax1 q.svc.pr n=3');
assert.equal(compose('q', { q: 'AI agents package pricing', n: 3, f: 't,u' }),
  'ax1 q q="AI agents package pricing" n=3 f=t,u');
assert.equal(quote('a"b\\c'), '"a\\"b\\\\c"');
assert.equal(unquote(quote('a"b\\c')), 'a"b\\c');
assert.equal(unquote('plain'), 'plain');

// decode — live-captured reply shape
const live = `ax1 ok op=o n=3 cov=1 cb=2 nx="a.quote i=<sku>; a.lead @ POST https://rainz.ai/wp-json/ax/v1/intent" nxu=https://rainz.ai/wp-json/ax/v1/x?s=ax1%20q.cat
=i:of-1|t:"AI implementation for business"|pr:quote|av:available|u:https://rainz.ai/|d:"Custom-scoped engagement; quote on enquiry"
=i:of-2|t:"Business stability architecture"|pr:quote|av:available|u:https://rainz.ai/|d:"Revenue, operations and data connected into one system"
+note d="Indicative and side-effect free."`;

const [a] = decode(live);
assert.equal(a.status, 'ok');
assert.equal(a.head.op, 'o');
assert.equal(a.head.cov, '1');
assert.equal(a.head.nx, 'a.quote i=<sku>; a.lead @ POST https://rainz.ai/wp-json/ax/v1/intent');
assert.equal(a.rows.length, 2);
assert.equal(a.rows[0].i, 'of-1');
assert.equal(a.rows[0].t, 'AI implementation for business');
assert.equal(a.rows[0].u, 'https://rainz.ai/'); // split at FIRST ':' only
assert.equal(a.rows[1].d, 'Revenue, operations and data connected into one system');
assert.equal(a.hints[0].name, 'note');
assert.equal(a.hints[0].d, 'Indicative and side-effect free.');

// decode — error
const [e] = decode('ax1 err code=missing_q d="s needs q=..."');
assert.equal(e.status, 'err');
assert.equal(e.head.code, 'missing_q');
assert.equal(e.head.d, 's needs q=...');

// decode — repair
const [r] = decode('ax1 rep? w=spce guess=spec conf=0.8 lx=3 d=https://rainz.ai/wp-json/rainz-axs/v1/lexicon\n+hint d="Unknown word. Nothing was executed."');
assert.equal(r.status, 'rep?');
assert.equal(r.head.guess, 'spec');
assert.equal(r.hints[0].d, 'Unknown word. Nothing was executed.');

// decode — stela (multiple answers)
const stela = decode('ax1 ok op=c n=1 cov=1 cb=2\n=t:A|u:https://x/a\n--\nax1 ok op=s n=1 cov=1 cb=2\n=t:B|u:https://x/b');
assert.equal(stela.length, 2);
assert.equal(stela[0].rows[0].t, 'A');
assert.equal(stela[1].rows[0].t, 'B');

// pipe inside quoted value
const [p] = decode('ax1 ok op=p cov=1 cb=1\n=t:"A | B"|d:plain');
assert.equal(p.rows[0].t, 'A | B');
assert.equal(p.rows[0].d, 'plain');

// client compose→URL (mock fetch)
let seen;
const ax = new AXSClient('https://rainz.ai/', {
  fetch: async (url, opts) => { seen = { url, opts }; return { ok: true, text: async () => 'ax1 ok op=c cov=1 cb=2', json: async () => ({}) }; },
});
await ax.ask('q.svc.pr', { n: 3 });
assert.equal(seen.url, 'https://rainz.ai/wp-json/ax/v1/x?s=ax1%20q.svc.pr%20n%3D3');
await ax.stela(['q.cat n=2', 'ax1 q.new']);
assert.equal(seen.opts.method, 'POST');
assert.equal(seen.opts.body, 'ax1 q.cat n=2\nax1 q.new');

console.log('all tests passed');
