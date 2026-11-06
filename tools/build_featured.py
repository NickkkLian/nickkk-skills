"""Rebuild the catalogue specimen from the bundled synthetic data and report spec."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/nk-data-story/skills/nk-data-story'
sys.path.insert(0, str(SKILL / 'scripts'))
import datafile
import render

example = SKILL / 'assets/example'
report_path = example / 'report.json'
report = json.loads(report_path.read_text())
input_path = example / report['data']['file']
table = datafile.read_table(str(input_path))
digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
page, errors, warnings = render.build(report, table, digest)
if errors:
    raise SystemExit('\n'.join(errors))
figure = next(f for f in report['figures'] if f['id'] == 'monday_share_q4')
result = datafile.compute(table, figure)
target = ROOT / 'docs/assets/featured'
target.mkdir(parents=True, exist_ok=True)
(target / 'report.html').write_text(page)
shutil.copy2(input_path, target / input_path.name)
shutil.copy2(report_path, target / 'report.json')
shutil.copy2(ROOT / 'gallery/results/nk-data-story.png', target / 'recorded-report.png')
record = {'synthetic': report['data']['synthetic'], 'input': input_path.name,
          'sha256': digest, 'figure': figure['id'], 'result': result,
          'window': figure['window'], 'check': 'Passed', 'warnings': warnings}
(target / 'evidence.json').write_text(json.dumps(record, indent=2) + '\n')
(ROOT / 'docs/featured-evidence.js').write_text('window.FEATURED_EVIDENCE = ' + json.dumps(record, indent=2) + ';\n')
print('Built synthetic report and specimen; report check passed.')
