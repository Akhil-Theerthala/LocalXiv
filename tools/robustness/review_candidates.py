"""Locate audit candidates despite PDF word-boundary differences; retain unresolved findings."""
import argparse
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from sample import ROOT, save
from audit import normalized, visible_text


def locate(anchor, text):
    positions = [i for i,c in enumerate(text) if not c.isspace()]
    compact = ''.join(text[i] for i in positions)
    target = ''.join(anchor.split())
    start = compact.find(target)
    if start < 0 or not target:
        return None
    left, right = positions[start], positions[start+len(target)-1]+1
    return text[max(0,left-100):min(len(text),right+100)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    for identifier, record in json.loads(args.results.read_text()).items():
        work = ROOT/record.get('directory','')
        audit_path = work/'fidelity-audit.json'
        if record['status'] != 'converted' or not audit_path.exists(): continue
        audit = json.loads(audit_path.read_text())
        if audit.get('status') == 'audit_failed': continue
        document = json.loads((work/'document.json').read_text())
        chapters = {}
        for chapter in document['chapters']:
            root = ET.parse(work/chapter['path']).getroot()
            head = root.find('{*}head')
            if head is not None: root.remove(head)
            chapters[chapter['path']] = normalized(visible_text(root))
        candidates = [{'kind':'prose', **entry} for entry in audit['missing_reader_anchor_examples']]
        candidates += [{'kind':'caption','text':text} for text in audit['missing_caption_anchors']]
        candidates += [{'kind':'note','text':entry['anchor']} for entry in audit['missing_note_anchors']]
        candidates += [{'kind':'table_text','text':text} for text in audit.get('missing_table_text_anchors',[])]
        for entry in candidates:
            matches = [{'chapter':name,'reader_context':context} for name,text in chapters.items() if (context:=locate(entry['text'],text))]
            entry['word_boundary_matches'] = matches
        save(work/'anchor-review.json', {'document_sha256':audit['document_sha256'],
             'meaning':'Exact letters and digits in order after ignoring word boundaries. This locates text; it does not certify its semantics or clear other audit findings.',
             'candidates':candidates, 'not_located':sum(not c['word_boundary_matches'] for c in candidates), 'audit_flags':audit['flags']})
        print(identifier, len(candidates), 'candidates;', sum(not c['word_boundary_matches'] for c in candidates), 'not located', flush=True)


if __name__ == '__main__':
    assert locate('a b c', 'before abc after') == 'before abc after'
    assert locate('a missing word', 'a word') is None
    main()
