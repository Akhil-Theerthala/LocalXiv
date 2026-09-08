"""Compare formula-rendering time and exact output against a frozen converter."""
import argparse
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
from unittest.mock import patch
from xml.etree import ElementTree as ET

from sample import CACHE, ROOT, save


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def trial(module, chapters, output):
    cache, calls, content = {}, [], {}
    trees = {name:ET.fromstring(data) for name,data in chapters.items()}
    original_run = subprocess.run
    def measured(*args, **kwargs):
        start = time.perf_counter()
        result = original_run(*args, **kwargs)
        calls.append({'program':Path(args[0][0]).name, 'seconds':time.perf_counter()-start})
        return result
    start = time.perf_counter()
    count = 0
    with patch('subprocess.run', side_effect=measured):
        if hasattr(module, '_render_math'):
            module._render_math([e for tree in trees.values() for e in tree.iter() if module.local(e.tag) == 'math'], cache)
        for name, tree in trees.items():
            directory = output / Path(name).parent
            directory.mkdir(parents=True, exist_ok=True)
            if 'render_cache' in inspect.signature(module._math_images).parameters:
                count += module._math_images(tree, directory, cache)
            else:
                count += module._math_images(tree, directory)
            content[name] = hashlib.sha256(ET.tostring(tree)).hexdigest()
    elapsed = time.perf_counter()-start
    content.update({p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob('*.png')})
    return {'seconds':elapsed, 'equations':count, 'processes':len(calls), 'calls':calls, 'content':content}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-stage', required=True)
    parser.add_argument('--paper', type=Path, action='append', required=True)
    parser.add_argument('--name', required=True)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    output = CACHE/'benchmarks'/args.name
    output.mkdir(parents=True, exist_ok=False)
    old_path = CACHE/'runs'/args.baseline_stage/'code/papers/document.py'
    new_path = ROOT/'papers/document.py'
    shutil.copy2(new_path, output/'candidate-document.py')
    shutil.copy2(old_path, output/'baseline-document.py')
    modules = {'baseline':load(old_path, 'baseline_document'), 'candidate':load(new_path, 'candidate_document')}
    report = {'scope':'Formula image rendering only, excluding retrieval, source parsing and EPUBCheck.',
              'code_hashes':{key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in [('baseline',old_path),('candidate',new_path)]},
              'load_average_before':os.getloadavg(), 'papers':{}}
    for paper in args.paper:
        document = json.loads((paper/'document.json').read_text())
        chapters = {c['path']:(paper/c['path']).read_bytes() for c in document['chapters']}
        rows = []
        expected = None
        for repeat in range(args.repeats):
            for key in (('baseline','candidate') if repeat % 2 == 0 else ('candidate','baseline')):
                result = trial(modules[key], chapters, output/paper.name/f'{repeat}-{key}')
                if expected is None: expected = result['content']
                result['identical_to_baseline'] = result['content'] == expected
                result.update(variant=key, repeat=repeat)
                rows.append(result)
                print(paper.name, key, round(result['seconds'],3), result['processes'], result['identical_to_baseline'], flush=True)
                report['papers'][str(paper)] = {'runs':rows}
                save(output/'results.json', report)
        medians = {key:statistics.median(r['seconds'] for r in rows if r['variant']==key) for key in modules}
        report['papers'][str(paper)].update(median_seconds=medians, reduction_percent=100*(1-medians['candidate']/medians['baseline']))
    report['load_average_after'] = os.getloadavg()
    save(output/'results.json', report)
    return int(any(not r['identical_to_baseline'] for p in report['papers'].values() for r in p['runs']))


if __name__ == '__main__':
    sys.exit(main())
