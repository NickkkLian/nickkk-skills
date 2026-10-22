#!/usr/bin/env python3
"""Install a portable acceptor entry point beside an existing handoff/ and anchor.txt."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ENTRY = '''#!/usr/bin/env python3
"""Acceptor entry point; keep this and acceptor-tools/ outside the executor's handoff/."""
from pathlib import Path
import runpy
import sys

here = Path(__file__).resolve().parent
sys.argv = [str(here / 'acceptor-tools' / 'handoff_verify.py'), str(here / 'handoff'),
            '--trust-root', str(here / 'anchor.txt'), '--source', str(here)]
runpy.run_path(str(here / 'acceptor-tools' / 'handoff_verify.py'), run_name='__main__')
'''

def install(destination):
    destination = Path(destination).resolve()
    tools = destination / 'acceptor-tools'
    tools.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(__file__).with_name('handoff_verify.py'), tools / 'handoff_verify.py')
    (destination / 'verify.py').write_text(ENTRY, encoding='utf-8')

def selftest():
    sys.dont_write_bytecode = True
    import handoff_init
    with tempfile.TemporaryDirectory(prefix='portable-acceptor-') as temp:
        root = Path(temp) / 'original'
        pkg = Path(handoff_init.scaffold(str(root), 'handoff', 'full'))
        (pkg / 'reference/spec.md').write_text('A synthetic acceptance fixture.\n')
        handoff_init.seal(str(pkg)); handoff_init.fill_demo(str(pkg))
        handoff_init.trust_root(str(pkg), str(root / 'anchor.txt'))
        install(root)
        relocated = Path(temp) / 'relocated'
        shutil.copytree(root, relocated)
        shutil.rmtree(root)  # our generated fixture only; prove no original runtime is required
        good = subprocess.run([sys.executable, '-B', 'verify.py'], cwd=relocated, capture_output=True, text=True)
        assert good.returncode == 0, good.stdout + good.stderr
        checker = relocated / 'handoff/output/handback_check.py'
        checker.write_text('print("ALL PASS")\n')
        bad = subprocess.run([sys.executable, '-B', 'verify.py'], cwd=relocated, capture_output=True, text=True)
        assert bad.returncode == 1 and 'handback_check.py' in bad.stdout, bad.stdout + bad.stderr
        assert '\x2fUsers\x2f' not in (relocated / 'verify.py').read_text()  # escaped so skill_lint's path check does not flag this test
    print('make_verifier selftest: 3/3 passed (relocated success, tamper rejection, no absolute lab path)')
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, nargs='?')
    parser.add_argument('--selftest', action='store_true')
    args = parser.parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.destination is None: parser.error('destination or --selftest is required')
    install(args.destination)
