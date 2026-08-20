import unittest

from axs_client import Answer, AXSClient, compose, decode, quote, unquote

LIVE = (
    'ax1 ok op=o n=3 cov=1 cb=2 nx="a.quote i=<sku>; a.lead @ POST '
    'https://rainz.ai/wp-json/ax/v1/intent" '
    "nxu=https://rainz.ai/wp-json/ax/v1/x?s=ax1%20q.cat\n"
    '=i:of-1|t:"AI implementation for business"|pr:quote|av:available'
    '|u:https://rainz.ai/|d:"Custom-scoped engagement; quote on enquiry"\n'
    '=i:of-2|t:"Business stability architecture"|pr:quote|av:available'
    '|u:https://rainz.ai/|d:"Revenue, operations and data connected into one system"\n'
    '+note d="Indicative and side-effect free."'
)


class TestCompose(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(compose("q.svc.pr", n=3), "ax1 q.svc.pr n=3")

    def test_quoting(self):
        self.assertEqual(
            compose("q", q="AI agents package pricing", n=3, f="t,u"),
            'ax1 q q="AI agents package pricing" n=3 f=t,u',
        )

    def test_quote_roundtrip(self):
        v = 'a"b\\c'
        self.assertEqual(unquote(quote(v)), v)
        self.assertEqual(unquote("plain"), "plain")

    def test_none_dropped(self):
        self.assertEqual(compose("do.lead", nm="D", fo=None), "ax1 do.lead nm=D")


class TestDecode(unittest.TestCase):
    def test_live_reply(self):
        (a,) = decode(LIVE)
        self.assertEqual(a.status, "ok")
        self.assertTrue(a.ok)
        self.assertEqual(a.head["op"], "o")
        self.assertEqual(a.cov, 1.0)
        self.assertEqual(
            a.head["nx"],
            "a.quote i=<sku>; a.lead @ POST https://rainz.ai/wp-json/ax/v1/intent",
        )
        self.assertEqual(len(a.rows), 2)
        self.assertEqual(a.rows[0]["i"], "of-1")
        self.assertEqual(a.rows[0]["t"], "AI implementation for business")
        # split at FIRST ':' only — URLs survive
        self.assertEqual(a.rows[0]["u"], "https://rainz.ai/")
        self.assertEqual(a.hints[0]["name"], "note")
        self.assertEqual(a.hints[0]["d"], "Indicative and side-effect free.")

    def test_error(self):
        (e,) = decode('ax1 err code=missing_q d="s needs q=..."')
        self.assertEqual(e.status, "err")
        self.assertFalse(e.ok)
        self.assertEqual(e.head["code"], "missing_q")
        self.assertEqual(e.head["d"], "s needs q=...")

    def test_repair(self):
        (r,) = decode(
            "ax1 rep? w=spce guess=spec conf=0.8 lx=3 "
            "d=https://rainz.ai/wp-json/rainz-axs/v1/lexicon\n"
            '+hint d="Unknown word. Nothing was executed."'
        )
        self.assertEqual(r.status, "rep?")
        self.assertEqual(r.head["guess"], "spec")
        self.assertEqual(r.hints[0]["d"], "Unknown word. Nothing was executed.")

    def test_stela(self):
        answers = decode(
            "ax1 ok op=c n=1 cov=1 cb=2\n=t:A|u:https://x/a\n--\n"
            "ax1 ok op=s n=1 cov=1 cb=2\n=t:B|u:https://x/b"
        )
        self.assertEqual(len(answers), 2)
        self.assertEqual(answers[0].rows[0]["t"], "A")
        self.assertEqual(answers[1].rows[0]["t"], "B")

    def test_pipe_inside_quotes(self):
        (p,) = decode('ax1 ok op=p cov=1 cb=1\n=t:"A | B"|d:plain')
        self.assertEqual(p.rows[0]["t"], "A | B")
        self.assertEqual(p.rows[0]["d"], "plain")


class TestClient(unittest.TestCase):
    def test_compose_url(self):
        ax = AXSClient("https://rainz.ai/")
        seen = {}
        def fake_get(url):
            seen["url"] = url
            return "ax1 ok op=c cov=1 cb=2"

        ax._get = fake_get
        a = ax.ask("q.svc.pr", n=3)
        self.assertEqual(
            seen["url"], "https://rainz.ai/wp-json/ax/v1/x?s=ax1%20q.svc.pr%20n%3D3"
        )
        self.assertIsInstance(a, Answer)
        self.assertTrue(a.ok)


if __name__ == "__main__":
    unittest.main()
