#!/usr/bin/env python3
"""Render a local page offline in installed Chrome/Chromium; never infer rendering from file checks.

    python3 render_check.py page.html
    python3 render_check.py --selftest
Exit: 0 built with the tick; 1 cross or script error; 2 not rendered / usage;
      3 built before this check existed, not judged.
"""
import os
import html
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

import numsrc


OBSERVER = '''<script id="nk-render-observer">
(function () {
  var root = document.documentElement;
  root.removeAttribute("data-nk-rendered");
  root.removeAttribute("data-nk-render-error");
  function error(text) { if (!root.hasAttribute("data-nk-render-error")) root.setAttribute("data-nk-render-error", text); }
  window.addEventListener("error", function (event) { if (event.message) error(event.message); });
  window.addEventListener("unhandledrejection", function (event) { error(event.reason && event.reason.message || String(event.reason)); });
  window.addEventListener("load", function () { root.setAttribute("data-nk-rendered", "yes"); });
})();
</script>'''


def find_browser():
    """No download, no user profile: just an installed Chrome/Chromium executable."""
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome"):
        found = shutil.which(name)
        if found:
            return [found]
    places = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
        "/usr/bin/chromium", "/usr/bin/google-chrome", "/opt/google/chrome/chrome",
    ]
    for variable in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        if os.environ.get(variable):
            places.append(str(Path(os.environ[variable]) / "Google/Chrome/Application/chrome.exe"))
            places.append(str(Path(os.environ[variable]) / "Chromium/Application/chrome.exe"))
    return next(([p] for p in places if Path(p).is_file()), None)


def classify(dom):
    """Inspect the dumped DOM, not authored JavaScript or browser exit-zero alone."""
    page = numsrc._Page(dom)
    root = next((n for n in page.nodes if n.tag == "html"), None)
    if root is None:
        return "not rendered: browser returned no page", 2
    if root.attrs.get("data-nk-rendered") != "yes" or not re.search(r'</html\s*>', dom, re.I):
        return "not rendered: browser returned no completed page", 2
    error = root.attrs.get("data-nk-render-error") or root.attrs.get("data-nk-build-error")
    if error:
        return "script error: " + error, 1
    if 'data-nk-build' not in root.attrs and not any(n.attrs.get('id') == 'nk-build-guard' for n in page.nodes):
        return "built before this check existed, not judged", 3
    eq = next((n for n in page.nodes if n.attrs.get("id") == "sum-eq"), None)
    verdicts = [n for n in page.nodes if eq and eq in numsrc._ancestors(n)
                and set((n.attrs.get("class") or "").split()) & {"ok", "bad"}]
    cross = next((n for n in verdicts if "bad" in (n.attrs.get("class") or "").split()), None)
    if cross:
        return "built with the cross: " + (cross.text().strip() or "no reason supplied"), 1
    marks = next((n for n in page.nodes if n.attrs.get("id") == "form-marks"), None)
    table = next((n for n in page.nodes if n.attrs.get("id") == "table"), None)
    rows_drawn = any(n.tag == "tr" and table in numsrc._ancestors(n)
                     and any(a.tag == "tbody" for a in numsrc._ancestors(n)) for n in page.nodes) if table else False
    marks_drawn = marks and any(isinstance(part, numsrc._Node) for part in marks.parts)
    if (root.attrs.get("data-nk-build") == "built" and marks_drawn and rows_drawn
            and any("ok" in (n.attrs.get("class") or "").split() for n in verdicts)):
        return "built with the tick", 0
    return "script error: page did not complete its drawing and sums", 1


def render(path, browser=None, discover=None):
    try:
        command = browser if browser is not None else (discover or find_browser)()
        if not command:
            return "no browser found, not rendered", 2
        path = Path(path).resolve()
        source = path.read_text(encoding="utf-8-sig")
        # A copied browser dump must not supply its own evidence of this render.
        source = re.sub(r'<html\b[^>]*>', lambda m: re.sub(
            r'''\sdata-nk-rendered(?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+))?''', '', m[0], flags=re.I),
            source, count=1, flags=re.I)
        # A diagnostic copy catches errors even in old pages that have no build guard.
        # Resolve local assets beside the original, and never change the user's file.
        base = '' if re.search(r'<base\b', source, re.I) else '<base href="' + html.escape(path.parent.as_uri() + '/', quote=True) + '">'
        source, count = re.subn(r'(<head\b[^>]*>)', lambda m: m[0] + base + OBSERVER, source, count=1, flags=re.I)
        if not count:
            return "not rendered: page has no head", 2
        with tempfile.TemporaryDirectory(prefix="nk-render-") as directory:
            scratch = Path(directory)
            copy = scratch / "page.html"
            copy.write_text(source, encoding="utf-8-sig")
            flags = ["--headless", "--dump-dom", "--no-first-run", "--no-default-browser-check",
                     "--disable-background-networking", "--disable-component-update", "--disable-sync",
                     "--disable-extensions", "--disable-default-apps", "--disable-client-side-phishing-detection",
                     "--disable-features=MediaRouter,OptimizationHints,AutofillServerCommunication",
                     "--host-resolver-rules=MAP * ~NOTFOUND", "--proxy-server=http://127.0.0.1:9",
                     "--proxy-bypass-list=<-loopback>", "--virtual-time-budget=2000",
                     "--user-data-dir=" + str(scratch / "profile"), copy.as_uri()]
            result = subprocess.run(command + flags, capture_output=True, text=True, timeout=25)
            answer = classify(result.stdout)
            # Chrome may print a completed DOM and then fail during shutdown.
            # The injected load marker and complete HTML, rather than exit-zero alone, are the evidence.
            if answer[1] != 2 or not result.returncode:
                return answer
            if result.returncode:
                detail = (' '.join(result.stderr.split()) or "exit " + str(result.returncode))[:500]
                return "not rendered: browser could not start or finish: " + detail, 2
    except (OSError, subprocess.SubprocessError, UnicodeError, RuntimeError) as exc:
        return "not rendered: " + ' '.join(str(exc).split()), 2


def selftest():
    """A fake command returns DOM, not JavaScript execution: no real browser is started."""
    lines = []
    def check(condition, label):
        lines.append("  " + ("PASS " if condition else "FAIL ") + label)
    def attempt(path, **options):
        # Preserve all negative results during the fail-first run, including an escaped exception.
        try:
            return render(path, **options)
        except Exception as exc:
            return "raised " + type(exc).__name__ + ": " + str(exc), -1
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        page = root / "page.html"
        page.write_text('<html data-nk-rendered="yes"><head></head><body>Fixture</body></html>', encoding="utf-8")
        fake = root / "fake_browser.py"
        fake.write_text('''import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
assert '--headless' in sys.argv and '--dump-dom' in sys.argv
assert '--incognito' not in sys.argv
assert not any(flag in sys.argv for flag in ('--no-sandbox', '--disable-setuid-sandbox', '--disable-web-security'))
assert '--disable-background-networking' in sys.argv
assert '--host-resolver-rules=MAP * ~NOTFOUND' in sys.argv
assert '--proxy-server=http://127.0.0.1:9' in sys.argv
assert '--proxy-bypass-list=<-loopback>' in sys.argv
copy = Path(unquote(urlparse(sys.argv[-1]).path))
assert '--user-data-dir=' + str(copy.parent / 'profile') in sys.argv
source = copy.read_text()
assert 'nk-render-observer' in source and '<base href=' in source
assert '<html data-nk-rendered="yes">' not in source
print(Path(sys.argv[1]).read_text())
''', encoding="utf-8")
        dom = root / "dom.html"
        shell = '<html data-nk-rendered="yes" data-nk-build="built"><body><div id="form-marks"><i></i></div><p id="sum-eq">{}</p><table id="table"><tbody><tr><td>row</td></tr></tbody></table></body></html>'
        for label, markup, expected, code in [
            ("tick", shell.format('<span class="ok">adds up</span>'), "built with the tick", 0),
            ("cross", shell.format('<span class="bad">parts do not add up</span>'), "built with the cross: parts do not add up", 1),
            ("error", '<html data-nk-rendered="yes" data-nk-render-error="configuration exploded"><body></body></html>', "script error: configuration exploded", 1),
        ]:
            dom.write_text(markup, encoding="utf-8")
            actual = render(page, browser=[sys.executable, str(fake), str(dom)])
            check(actual == (expected, code), label + ": " + actual[0])
        dom.write_text(shell.format('<span class="ok">adds up</span>'), encoding="utf-8")
        # A real Chrome can dump the complete page and still exit non-zero.
        printed = root / 'printed_then_failed.py'
        printed.write_text('import sys\nfrom pathlib import Path\nprint(Path(sys.argv[1]).read_text())\nprint("shutdown diagnostic", file=sys.stderr)\nsys.exit(2)\n', encoding="utf-8")
        actual = attempt(page, browser=[sys.executable, str(printed), str(dom)])
        check(actual == ('built with the tick', 0), 'complete DOM survives browser exit 2: ' + actual[0])
        legacy = shell.format('<span class="ok">adds up</span>').replace(' data-nk-build="built"', '')
        dom.write_text(legacy, encoding="utf-8")
        legacy_browser = root / 'legacy_browser.py'
        legacy_browser.write_text('import sys\nfrom pathlib import Path\nprint(Path(sys.argv[1]).read_text())\n', encoding='utf-8')
        actual = attempt(page, browser=[sys.executable, str(legacy_browser), str(dom)])
        check(actual == ('built before this check existed, not judged', 3), 'earlier starter is not judged: ' + actual[0])
        def denied():
            raise PermissionError('browser read denied by sandbox')
        actual = attempt(page, discover=denied)
        check(actual == ('not rendered: browser read denied by sandbox', 2), 'discovery read denied: ' + actual[0])
        cli = root / 'denied_discovery_cli.py'
        cli.write_text('import sys\nfrom unittest.mock import patch\nsys.path.insert(0, ' + repr(str(Path(__file__).resolve().parent)) + ')\nimport render_check\nwith patch.object(render_check.shutil, "which", return_value=None), patch.object(render_check.Path, "is_file", side_effect=PermissionError("browser read denied by sandbox")):\n    sys.exit(render_check.main(sys.argv[1:]))\n', encoding='utf-8')
        result = subprocess.run([sys.executable, str(cli), str(page)], capture_output=True, text=True)
        check(result.returncode == 2 and result.stdout.strip() == 'not rendered: browser read denied by sandbox'
              and not result.stderr, 'denied fixed install path: CLI exit 2, plain answer, no traceback (exit ' + str(result.returncode) + ')')
        # It exists, but a direct start is forbidden: use discovery, not an explicit browser override.
        unstartable = root / 'found_browser'
        unstartable.write_text('fake browser, not executable', encoding='utf-8')
        unstartable.chmod(0o600)
        actual = attempt(page, discover=lambda: [str(unstartable)])
        check(actual[0].startswith('not rendered:') and actual[1] == 2, 'found but cannot start: ' + actual[0])
        actual = render(page, discover=lambda: None)
        check(actual == ("no browser found, not rendered", 2), actual[0])
        # These do not discover or start a real browser either.
        actual = render(page, browser=[str(root / "missing-browser")])
        check(actual[0].startswith("not rendered:") and actual[1] == 2, "blocked/unavailable command cannot claim a build")
        fake.write_text('import sys\nprint("sandbox denied", file=sys.stderr)\nsys.exit(1)\n', encoding="utf-8")
        actual = render(page, browser=[sys.executable, str(fake)])
        check(actual == ("not rendered: browser could not start or finish: sandbox denied", 2), "sandbox refusal is not rendered")
        check(classify('<html><body><span class="ok">adds up</span></body></html>')[1] == 2,
              "exit-zero/static tick without completed DOM is not rendered")
        check(classify('<html data-nk-rendered="yes" data-nk-build="pending"><body></body></html>')[0].startswith("script error:"),
              "a rendered empty page cannot pass")
        no_marks = shell.format('<span class="ok">adds up</span>').replace('<i></i>', '')
        no_rows = shell.format('<span class="ok">adds up</span>').replace('<tr><td>row</td></tr>', '')
        check(classify(no_marks)[1] == 1 and classify(no_rows)[1] == 1,
              "a tick without drawn marks or rows cannot pass")
    print('render_check selftest · ' + str(sum('  PASS ' in line for line in lines)) + '/' + str(len(lines)) + ' passed')
    print('\n'.join(lines))
    return 0 if all('  PASS ' in line for line in lines) else 2


def main(argv):
    if argv == ["--selftest"]:
        return selftest()
    if len(argv) != 1:
        print(__doc__)
        return 2
    message, code = render(Path(argv[0]))
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
