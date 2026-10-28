"""Run from repository root: python -m unittest discover -s tests -v"""
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
import unittest
import json
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'fetch_news.py'
spec = importlib.util.spec_from_file_location('fetch_news', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NOW=datetime(2026,10,29,10,0,tzinfo=timezone.utc)
RSS=b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Blog</title>
<item><title>New retention &amp; growth report</title><link>https://example.com/p/1?utm_source=a</link><pubDate>Wed, 28 Oct 2026 10:00:00 GMT</pubDate><description><![CDATA[<p>Important <b>retention</b> news</p><script>evil()</script>]]></description></item>
<item><title>Old blog post</title><link>https://example.com/p/old</link><pubDate>Sun, 01 Jan 2023 10:00:00 GMT</pubDate></item>
</channel></rss>'''
ATOM=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom Story</title><link rel="alternate" href="https://example.com/atom1"/><published>2026-10-27T13:00:00Z</published><summary>Readable summary</summary></entry></feed>'''

class FeedsTest(unittest.TestCase):
    def setUp(self):
        self.src={'id':'ns01','name':'Gainsight','url':'https://example.com/blog','type':'Blog','mode':'auto'}
    def test_rss(self):
        items=mod.parse_xml(RSS,self.src,'Resmi RSS/Atom',NOW)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['date'],'2026-10-28')
        self.assertEqual(items[0]['url'],'https://example.com/p/1')
        self.assertIn('retention',items[0]['summary'])
        self.assertNotIn('evil',items[0]['summary'])
    def test_atom(self):
        items=mod.parse_xml(ATOM,self.src,'RSS',NOW)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['title'],'Atom Story')
    def test_auto_discovery(self):
        html='<head><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head>'
        original=mod.get
        mod.get=lambda url:(html.encode(),'https://example.com/blog')
        try:self.assertEqual(mod.discovered_feed('https://example.com/blog'),'https://example.com/feed.xml')
        finally:mod.get=original
    def test_collector_keeps_existing_daily_digest_and_history(self):
        """Re-fetching feeds must not erase yesterday's briefing or cause needless AI calls."""
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            config=root/'sources.json'
            news=root/'news.json'
            config.write_text(json.dumps({'sources':[self.src]}),encoding='utf-8')
            previous={'articles':[], 'dailyDigest':{'date':'2026-10-28','mode':'ai','articleIds':['id1']},
                      'digestHistory':[{'date':'2026-10-28','mode':'ai'}]}
            news.write_text(json.dumps(previous),encoding='utf-8')
            orig=(mod.CONFIG,mod.DEST,mod.collect_source)
            try:
                mod.CONFIG=config;mod.DEST=news
                mod.collect_source=lambda src,now:([],{'id':src['id'],'name':src['name'],'status':'ok','count':0})
                mod.main()
                result=json.loads(news.read_text(encoding='utf-8'))
                self.assertEqual(result['dailyDigest'],previous['dailyDigest'])
                self.assertEqual(result['digestHistory'],previous['digestHistory'])
            finally:
                mod.CONFIG,mod.DEST,mod.collect_source=orig

    def test_collection_fallback(self):
        original_get=mod.get
        original_discovery=mod.discovered_feed
        mod.discovered_feed=lambda url: ''
        mod.get=lambda url:(RSS,url) if 'news.google.com' in url else (_ for _ in ()).throw(RuntimeError('down'))
        try:
            res,status=mod.collect_source(self.src,NOW)
            self.assertEqual(len(res),1)
            self.assertEqual(status['status'],'ok')
            self.assertEqual(status['provider'],'Google News RSS')
        finally:
            mod.get=original_get;mod.discovered_feed=original_discovery

if __name__=='__main__':unittest.main()