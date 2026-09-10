import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from app.server import Application
from papers.recommendations import CACHE_ID, DAY, discover, fingerprint, recommend, conference_records


class RecommendationTests(unittest.TestCase):
    def test_public_search_excludes_saved_versions_and_uses_canonical_links(self):
        feed = b'''<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><id>http://arxiv.org/abs/2501.00001v2</id><title>Uncertainty calibration</title><summary>Same paper</summary></entry>
        <entry><id>http://arxiv.org/abs/2501.00002v1</id><title>Related uncertainty paper</title><summary>Public abstract.</summary></entry></feed>'''
        response = Mock(); response.__enter__ = Mock(return_value=response); response.__exit__ = Mock(return_value=False); response.read.side_effect = [json.dumps({'result':{'hits':{'hit':[{'info':{'title':title,'venue':'ICML','year':'2025','key':'conf/icml/example','type':'Conference and Workshop Papers'}} for title in ['Uncertainty calibration','Related uncertainty paper']]}}}).encode(),feed]
        with patch('papers.recommendations.build_opener') as opener:
            opener.return_value.open.return_value = response
            items = discover([{'id': '2501.00001v1', 'title': 'Uncertainty calibration'}])
        self.assertEqual([p['id'] for p in items], ['2501.00002v1'])
        self.assertEqual(items[0]['url'], 'https://arxiv.org/abs/2501.00002v1')
        provider = Mock(settings={})
        provider.complete.return_value = {'text': json.dumps({'items': [{'id': items[0]['id'], 'summary': 'A brief description.', 'url': 'https://evil.test'}]})}
        self.assertEqual(recommend(provider, [], items)[0]['url'], items[0]['url'])
        provider.complete.assert_called_once()
        self.assertIn(datetime.date.today().isoformat(),provider.complete.call_args.args[0][0]['content'])
        self.assertEqual(recommend(provider, [], items)[0]['venue'],'ICML')
        provider.complete.return_value = {'text': '{"items":[{"id":"invented","summary":"Made up"}]}'}
        with self.assertRaises(ValueError):
            recommend(provider, [], items)

    def test_excludes_old_unverified_and_workshop_records(self):
        base = {'title':'Uncertainty in language models','venue':'ICML','year':'2025','key':'conf/icml/example','type':'Conference and Workshop Papers'}
        records = [base,{**base,'venue':'ICML Workshops'},{**base,'year':'2010'},{**base,'year':'2030'},{**base,'venue':'CoRR'},{**base,'venue':'ACL','ee':'https://aclanthology.org/2025.findings-acl.1/'}]
        actual=conference_records({'result':{'hits':{'hit':[{'info':r} for r in records]}}},[{'title':'Uncertainty in language models'}],datetime.date(2026,9,6))
        self.assertEqual(len(actual),1)
        self.assertEqual(actual[0]['venue'],'ICML')

    def test_cache_gates_keys_daily_refresh_new_papers_and_failure_backoff(self):
        with tempfile.TemporaryDirectory() as root:
            app = Application(Path(root)); app.close(); app.worker.join(3)
            settings = {'endpoint':'https://example.test/v1', 'model':'test', 'has_key':True}
            papers = [{'id':'2501.00001v1', 'title':'Calibration'}]
            with patch.object(app, 'submit') as submit:
                self.assertEqual(app.recommendations(papers, {**settings,'has_key':False}), {'items':[]})
                app.recommendations([],settings); submit.assert_not_called()
                app.recommendations(papers,settings); submit.assert_called_once()
                # No repeat even if the worker failed, was cancelled, or app restarted.
                app.recommendations(papers,settings); submit.assert_called_once()
                cache = app.library.get_generation(CACHE_ID,'recommendations')
                cache['attempted_at'] -= DAY
                app.library.save_generation(CACHE_ID,'recommendations',cache)
                app.recommendations(papers,settings); self.assertEqual(submit.call_count,2)
                app.recommendations(papers+[{'id':'2501.00002v1','title':'Related'}],settings)
                self.assertEqual(submit.call_count,3)

    def test_worker_has_no_request_caps_and_keeps_cache_on_failure(self):
        with tempfile.TemporaryDirectory() as root:
            app = Application(Path(root))
            try:
                settings = {'endpoint':'https://example.test/v1','model':'test'}
                app.library.save_settings(settings)
                app.library.save_paper('2501.00001v1', {'title':'Calibration'}, root)
                papers = app.library.list_papers()
                old = {'items':[{'id':'2501.00002v1','title':'Previous','summary':'Saved result.'}], 'fingerprint':fingerprint(papers,settings),'attempted_at':1}
                app.library.save_generation(CACHE_ID,'recommendations',old)
                with patch('app.server.get_key',return_value='test-key'), patch('app.server.discover',return_value=[{}]), patch('app.server.recommend',side_effect=ValueError('Invalid provider response')), patch('app.server.Provider') as provider:
                    job = app.submit('recommend',{'fingerprint':old['fingerprint']}); app.queue.join()
                    self.assertEqual(app.library.get_job(job['id'])['state'],'failed')
                    self.assertEqual(app.library.get_generation(CACHE_ID,'recommendations')['items'],old['items'])
                    passed = provider.call_args.args[0]
                    self.assertTrue({'max_context_chars', 'max_output_tokens', 'timeout'}.isdisjoint(passed))
            finally:
                app.close(); app.worker.join(3)
