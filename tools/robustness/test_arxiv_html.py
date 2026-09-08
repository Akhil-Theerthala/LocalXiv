import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from papers.arxiv_html import asset_url, check_svg, image_suffix, parse_article, prepare, retrieve

HTML='''<html><script>never copied</script><article class="ltx_document"><h1>A paper</h1><p>Before <math intent=":literal"><mi>x</mi></math> after.</p><figure><svg viewBox="0 0 100 50"><foreignObject width="100" height="50"><span>Diagram <math><mi>y</mi></math></span></foreignObject></svg><figcaption>A diagram.</figcaption></figure></article></html>'''

class ArxivHTMLTests(unittest.TestCase):
    def test_math_text_keeps_html_citations_and_math_alignment_namespaces(self):
        root,_=parse_article('<article class="ltx_document"><p><math><mtext>By <cite><a href="#ref">Smith</a></cite><malignmark/></mtext></math></p><p id="ref">Reference</p></article>','Citation')
        self.assertIsNotNone(root.find('.//{http://www.w3.org/1999/xhtml}cite'))
        self.assertIsNotNone(root.find('.//{http://www.w3.org/1998/Math/MathML}malignmark'))
        self.assertEqual(root.find('.//{*}a').get('href'),'#ref')

    def test_namespaces_math_and_diagram_labels_survive(self):
        root,report=parse_article(HTML,'A paper')
        self.assertEqual(len(root.findall('.//{http://www.w3.org/1998/Math/MathML}math')),2)
        svg=root.find('.//{http://www.w3.org/2000/svg}svg')
        self.assertEqual(svg.get('viewBox'),'0 0 100 50')
        self.assertEqual(svg.find('.//{http://www.w3.org/1999/xhtml}span').text,'Diagram ')
        self.assertNotIn('never copied',''.join(root.itertext()))
        self.assertEqual(report['mathml4_intents_retained_in_original_html'],1)

    def test_resource_boundaries(self):
        page='https://arxiv.org/html/2401.00001v1'
        self.assertEqual(asset_url(page,'2401.00001v1/fig.png'),page+'/fig.png')
        for value in ['https://other.example/fig.png','2401.00002v1/fig.png','2401.00001v1/%2e%2e/fig.png','data:image/png;base64,abc']:
            with self.subTest(value=value),self.assertRaises(ValueError):asset_url(page,value)

    def test_svg_cannot_fetch_external_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'f.svg'
            for body in ['<script/>','<image href="https://other.example/fig.png"/>','<style>@import "https://other.example/x.css";</style>']:
                p.write_text('<svg xmlns="http://www.w3.org/2000/svg">'+body+'</svg>')
                with self.assertRaises(ValueError):check_svg(p)
        with self.assertRaises(ValueError):
            parse_article('<article class="ltx_document"><svg><image href="https://other.example/f.png"/></svg></article>','Unsafe image')

    def test_cached_figure_bytes_are_verified_and_retrieval_is_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);meta={'arxiv_id':'2401.00001v1','title':'A paper'}
            html=HTML.replace('<figure>','<figure><object type="image/svg+xml" data="2401.00001v1/fig.svg"></object>')+'arXiv:2401.00001v1'
            def fetch(url,path,limit):
                path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Figure content</text></svg>' if url.endswith('.svg') else html)
            with patch('papers.arxiv_html.download',side_effect=fetch) as download:
                manifest=retrieve(root,meta);retrieve(root,meta)
                self.assertEqual(download.call_count,2)
            attempt=root/'attempt';attempt.mkdir();prepare(root,attempt,meta)
            text=(attempt/'reader/main.xhtml').read_text()
            self.assertIn('img',text);self.assertIn('A diagram.',text)
            (root/'arxiv-html'/manifest['assets'][0]['file']).write_text('changed')
            second=root/'second';second.mkdir()
            with self.assertRaisesRegex(ValueError,'changed'):prepare(root,second,meta)

    def test_page_without_the_requested_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('papers.arxiv_html.download',side_effect=lambda url,path,limit:path.write_text(HTML)):
                with self.assertRaisesRegex(ValueError,'version'):retrieve(Path(tmp),{'arxiv_id':'2401.00001v1','title':'A paper'})

    def test_retrieval_normalizes_misnamed_bytes_and_rejects_malformed_media(self):
        meta={'arxiv_id':'2402.07834v2','title':'A paper'}
        jpeg=b'\xff\xd8\xffjpeg'
        with tempfile.TemporaryDirectory() as tmp:
            for extension in ('png', 'jpg', 'jpeg'):
                root=Path(tmp)/extension
                root.mkdir()
                html='<article class="ltx_document"><img src="2402.07834v2/figure.'+extension+'"/></article>arXiv:2402.07834v2'
                def fetch(url,path,limit,html=html):
                    if '/figure.' in url:
                        path.write_bytes(jpeg)
                    else:
                        path.write_text(html)
                with patch('papers.arxiv_html.download',side_effect=fetch):
                    manifest=retrieve(root,meta)
                self.assertTrue(manifest['assets'][0]['file'].endswith('.jpg'))
            bad=Path(tmp)/'bad'
            html='<article class="ltx_document"><img src="2402.07834v2/figure.png"/></article>arXiv:2402.07834v2'
            def fetch_bad(url,path,limit):
                path.write_bytes(b'not an image') if '/figure.' in url else path.write_text(html)
            bad.mkdir()
            with patch('papers.arxiv_html.download',side_effect=fetch_bad), self.assertRaisesRegex(ValueError,'supported image'):
                retrieve(bad,meta)

    def test_prepare_normalizes_legacy_cached_jpeg_before_packaging(self):
        jpeg=b'\xff\xd8\xffjpeg'
        identifier='2402.07834v2'
        page='https://arxiv.org/html/'+identifier
        html='<article class="ltx_document"><img src="'+identifier+'/figure.png"/></article>'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cache=root/'arxiv-html';cache.mkdir()
            source=cache/'legacy.png';source.write_bytes(jpeg)
            raw=cache/'original.html';raw.write_text(html)
            (cache/'manifest.json').write_text(json.dumps({
                'url':page, 'html_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
                'assets':[{'url':page+'/figure.png','file':source.name,
                           'sha256':hashlib.sha256(jpeg).hexdigest()}]}))
            attempt=root/'attempt';attempt.mkdir()
            prepare(root,attempt,{'arxiv_id':identifier,'title':'A paper'})
            output=attempt/'reader'/('legacy.jpg')
            self.assertEqual(output.read_bytes(),jpeg)
            self.assertFalse((attempt/'reader/legacy.png').exists())

class RecoveryTests(unittest.TestCase):
    def test_html_failure_keeps_pdf_fallback_and_cancellation_propagates(self):
        from app.server import Application,Cancelled
        app=Application.__new__(Application)
        with tempfile.TemporaryDirectory() as tmp,patch.object(app,'checkpoint'),patch.object(app,'pdf_fallback',return_value={'format':'pdf'}) as pdf:
            with patch('papers.arxiv_html.retrieve',side_effect=ValueError('No rendered HTML')),patch('papers.convert.convert_paper',side_effect=ValueError('Source failed')):
                self.assertEqual(app.source_fallback({'id':'job'},Path(tmp),{},ValueError('Source failed')),{'format':'pdf'})
            pdf.assert_called_once()
            with patch('papers.arxiv_html.retrieve',side_effect=Cancelled):
                with self.assertRaises(Cancelled):app.source_fallback({'id':'job'},Path(tmp),{},ValueError('Source failed'))

    def test_html_failure_still_tries_latexml_when_source_exists(self):
        from app.server import Application
        app=Application.__new__(Application)
        with tempfile.TemporaryDirectory() as tmp,patch.object(app,'checkpoint'),patch.object(app,'pdf_fallback') as pdf:
            with patch('papers.arxiv_html.retrieve',side_effect=ValueError('No HTML')),patch('papers.convert.convert_paper',return_value={'converter':'latexml'}) as convert:
                self.assertEqual(app.source_fallback({'id':'job'},Path(tmp),{},ValueError('Pandoc failed')),{'converter':'latexml'})
                self.assertEqual(convert.call_args.kwargs,{'source_engine':'latexml'})
                pdf.assert_not_called()
                convert.reset_mock()
                app.source_fallback({'id':'job'},Path(tmp),{},ValueError('No source'),source_unavailable=True)
                convert.assert_not_called()
                pdf.assert_called_once()

    def test_valid_cached_html_uses_the_isolated_html_worker(self):
        from app.server import Application
        app=Application.__new__(Application)
        with tempfile.TemporaryDirectory() as tmp,patch.object(app,'checkpoint'),patch('papers.arxiv_html.retrieve'),patch('papers.convert.convert_paper',return_value={'converter':'arxiv-html'}) as convert:
            app.source_fallback({'id':'job'},Path(tmp),{'arxiv_id':'2401.00001v1'},ValueError('Source failed'))
            self.assertTrue(convert.call_args.kwargs['html_only'])

class ListingTests(unittest.TestCase):
    def test_embedded_listing_keeps_exact_code_and_line_targets(self):
        import base64
        code='if x:\n    print("value")\n'
        payload=base64.b64encode(code.encode()).decode()
        html='<article class="ltx_document"><div id="code" class="ltx_listing"><div class="ltx_listing_data"><a download="code.py" href="data:text/plain;base64,'+payload+'">⬇</a></div><div id="line1" class="ltx_listingline"><span class="ltx_tag">1</span><span>if x:</span></div><div id="line2" class="ltx_listingline"><span class="ltx_tag">2</span><span>    print(“value”)</span></div></div></article>'
        root,_=parse_article(html,'Listing')
        pre=root.find('.//{*}pre')
        self.assertIsNotNone(pre)
        self.assertEqual(''.join(pre.itertext()),code)
        self.assertIsNotNone(pre.find('.//*[@id="line2"]'))
        self.assertNotIn('data:',str([e.attrib for e in root.iter()]))
        with self.assertRaises(ValueError):parse_article(html.replace('if x:</span>','if z:</span>'),'Listing')

class CaptionGroupTests(unittest.TestCase):
    def test_multiple_tables_in_one_float_keep_each_caption(self):
        html='<article class="ltx_document"><figure id="tables">\n<figcaption>First.</figcaption><div><table><tr><td>One</td></tr></table></div><figcaption>Second.</figcaption><div><table><tr><td>Two</td></tr></table></div>\n</figure></article>'
        root,_=parse_article(html,'Tables')
        group=root.find('.//*[@id="tables"]')
        self.assertEqual(len(group.findall('./{*}figure')),2)
        self.assertEqual(''.join(group.itertext()).strip(),'First.OneSecond.Two')
        for f in group:self.assertEqual(len(f.findall('./{*}figcaption')),1)

    def test_notes_after_a_middle_caption_keep_their_order(self):
        html='<article class="ltx_document"><figure id="table"><div><table><tr><td>Value</td></tr></table></div><figcaption>Caption.</figcaption><div id="note">Following note.</div></figure></article>'
        root,_=parse_article(html,'Table')
        group=root.find('.//*[@id="table"]')
        self.assertTrue(group.tag.endswith('}div'))
        self.assertTrue(group[0][-1].tag.endswith('}figcaption'))
        self.assertEqual(group[1].get('id'),'note')
        self.assertEqual(''.join(group.itertext()),'ValueCaption.Following note.')

    def test_caption_only_float_adopts_adjacent_media_without_reordering(self):
        html='<article class="ltx_document"><div><div id="media"><img src="2401.00001v1/a.png"/></div><figure id="fig" class="ltx_figure"><figcaption>The image.</figcaption></figure></div></article>'
        root,report=parse_article(html,'Figure')
        figure=root.find('.//{*}figure')
        self.assertIsNotNone(figure.find('.//{*}img'))
        self.assertEqual(report['caption_groups'][0]['id'],'fig')
        other,_=parse_article(html.replace('<img src=', 'Unrelated paragraph. <img src='),'Figure')
        self.assertIsNone(other.find('.//{*}figure/{*}div'))

    def test_block_wrappers_keep_prose_in_reading_order(self):
        html='<article class="ltx_document"><p>Before <span><div><p>Inside</p></div></span> after.</p></article>'
        root,_=parse_article(html,'Blocks')
        for e in root.iter():
            if e.tag.endswith('}p') or e.tag.endswith('}span'):
                self.assertFalse(any(c.tag.endswith('}div') for c in e))
        self.assertEqual(''.join(root.find('.//{*}article').itertext()),'Before Inside after.')

class EmbeddedRasterTests(unittest.TestCase):
    def test_image_type_comes_from_bytes_not_filename(self):
        jpeg = b'\xff\xd8\xff' + b'jpeg'
        self.assertEqual(image_suffix(jpeg), '.jpg')
        self.assertEqual(image_suffix(b'\x89PNG\r\n\x1a\n' + b'png'), '.png')
        with self.assertRaisesRegex(ValueError, 'supported image'):
            image_suffix(b'not an image')

    def test_svg_accepts_embedded_png_but_rejects_active_data(self):
        import base64
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'image.svg'
            png='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
            p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="'+png+'"/></svg>')
            check_svg(p)
            p.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/svg+xml;base64,PHN2Zy8+"/></svg>')
            with self.assertRaises(ValueError):check_svg(p)

class EmptyContactTests(unittest.TestCase):
    def test_empty_mail_link_retains_contact_text_and_real_inner_link(self):
        from papers.document import _safe_xhtml
        root,_=parse_article('<article class="ltx_document"><p><a href="mailto:"><a href="mailto:author@example.org">Author</a> {a,b}@example.org</a></p></article>','Contact')
        _safe_xhtml(root)
        links=root.findall('.//{*}a')
        self.assertEqual([e.get('href') for e in links],['mailto:author@example.org'])
        self.assertIn('{a,b}@example.org',''.join(root.itertext()))

class FlexCaptionTests(unittest.TestCase):
    def test_single_column_flex_rows_preserve_table_caption_pairing(self):
        html='<article class="ltx_document"><div class="ltx_flex_figure"><div class="ltx_flex_cell"><table><tr><td>42</td></tr></table></div><div class="ltx_flex_break"></div><div class="ltx_flex_cell"><figure id="table" class="ltx_table"><figcaption>Measured result</figcaption></figure></div></div></article>'
        root,_=parse_article(html,'Table')
        self.assertEqual(root.find('.//{*}figure//{*}td').text,'42')
        table='<div class="ltx_flex_cell"><table><tr><td>42</td></tr></table></div>'
        caption='<div class="ltx_flex_cell"><figure id="table" class="ltx_table"><figcaption>Measured result</figcaption></figure></div>'
        reverse=html.replace(table,'PLACEHOLDER').replace(caption,table).replace('PLACEHOLDER',caption)
        first,_=parse_article(reverse,'Caption first')
        self.assertEqual(''.join(first.find('.//{*}figure').itertext()),'Measured result42')
        ambiguous=html.replace('<div class="ltx_flex_figure">','<div class="ltx_flex_figure"><div class="ltx_flex_cell"><table><tr><td>99</td></tr></table></div>')
        other,_=parse_article(ambiguous,'Ambiguous columns')
        self.assertIsNone(other.find('.//{*}figure//{*}td'))
