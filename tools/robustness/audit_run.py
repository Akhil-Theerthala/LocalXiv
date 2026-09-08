"""Audit completed outputs and compare content with an earlier reviewed stage."""
import argparse
import json
from sample import CACHE, ROOT, save
from audit import audit
from integrity import read_document, compare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True)
    parser.add_argument('--compare-stage')
    args=parser.parse_args()
    results=json.loads((CACHE/'runs'/args.stage/'results.json').read_text())
    downloads=json.loads((CACHE/'downloads.json').read_text())
    for identifier, record in results.items():
        if record['status']!='converted':continue
        work=ROOT/record['directory']
        target=work/'fidelity-audit.json'
        print('AUDIT',identifier,flush=True)
        try:
            item=audit({'id':identifier,'title':record['title'],
                        'directory':downloads[identifier]['directory'],
                        'source_file':'source','pdf_file':'original.pdf'},work)
            save(target,item)
            snapshot=read_document(work)
            save(work/'content-snapshot.json',snapshot)
            if args.compare_stage:
                previous=CACHE/'runs'/args.compare_stage/identifier/'content-snapshot.json'
                if previous.exists():save(work/'content-changes.json',compare(json.loads(previous.read_text()),snapshot))
            print('AUDIT RESULT',identifier,item['status'],item.get('flags',[]),flush=True)
        except Exception as error:
            save(target,{'id':identifier,'status':'audit_failed','error':str(error)})
            print('AUDIT FAILED',identifier,str(error),flush=True)


if __name__=='__main__':main()
