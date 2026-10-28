import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('digest',(HERE/'scripts/build_digest.py'))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DigestTest(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,29,7,0,0,tzinfo=timezone.utc)
        self.sources={'ns01':{'id':'ns01','name':'Gainsight','category':'Customer Success ve CX','priority':'Yüksek'},'ns02':{'id':'ns02','name':'OpenAI','category':'Yapay Zekâ','priority':'Yüksek'}}
    def article(self,tag,hours=2,source='ns01',description=''):
        pub=self.now-timedelta(hours=hours)
        return dict(id=tag,sourceId=source,title='SaaS growth strategy '+tag,provider='Google News RSS',date=pub.date().isoformat(),publishedAt=pub.isoformat(),url='https://example.com/'+tag,summary=description)
    def test_selection_and_scope(self):
        data={'articles':[self.article('a'),self.article('b',50,source='ns02')]}
        selected,scope,n=mod.select_articles(data,self.sources,self.now)
        self.assertEqual(scope,'last24h')
        self.assertEqual(len(selected),1)
    def test_recent_fallback(self):
        data={'articles':[self.article('a',25),self.article('b',100,source='ns02')]}
        selected,scope,n=mod.select_articles(data,self.sources,self.now)
        self.assertEqual(scope,'last7d')
        self.assertEqual(len(selected),2)
    def test_no_invented_text_if_only_title(self):
        article=self.article('a')
        digest=mod.no_ai_digest([article],self.sources)
        self.assertEqual(digest['cards'][0]['basis'],'title_only')
        self.assertIn('Yalnızca yayın başlığı',digest['cards'][0]['summary'])
    def test_rss_description_retained(self):
        article=self.article('a',description='Official description, short text.')
        digest=mod.no_ai_digest([article],self.sources)
        self.assertEqual(digest['cards'][0]['summary'],'Official description, short text.')

if __name__=='__main__':unittest.main()