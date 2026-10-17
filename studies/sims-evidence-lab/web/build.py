"""Build self-contained SIMS pages with synchronous startup and local state."""
from pathlib import Path
from html import escape
import json
import re

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
DIST = ROOT / 'dist'
PAGES = [
    ('index.html', 'Latest run', 'sims-repeated-rounds', True),
    ('sims-repeated-rounds.html', 'Repeated rounds', 'sims-repeated-rounds', False),
    ('sims-evidence-and-response.html', 'Evidence & response', 'sims-evidence-and-response', False),
    ('sims-claim-testing.html', 'Claims & actions', 'sims-claim-testing', False),
    ('sims-network.html', 'Network', 'sims-network', False),
]
REPO = 'https://github.com/NousVolition/Nous-Volition/tree/main/studies/sims-evidence-lab'
STYLE = '''
html,body{margin:0}body{box-sizing:border-box;padding:1rem!important}
.sims-site-nav,main,.sims-startup{max-width:1400px;margin-left:auto;margin-right:auto}
.sims-site-nav{font:14px/1.5 system-ui,sans-serif;margin-bottom:1.25rem;padding-bottom:1rem;border-bottom:1px solid var(--border);color:var(--foreground)}
.sims-site-nav .sims-brand{display:flex;align-items:baseline;gap:.7rem;margin-bottom:.6rem}
.sims-site-nav strong{font-size:20px;letter-spacing:.05em}.sims-site-nav span{opacity:.7}
.sims-site-nav .sims-links{display:flex;flex-wrap:wrap;gap:.3rem .4rem;align-items:center}
.sims-site-nav a{color:inherit;text-decoration:none;display:inline-block;padding:.4rem .65rem;border-radius:6px}
.sims-site-nav a:hover,.sims-site-nav a:focus-visible{background:color-mix(in srgb,currentColor 10%,transparent);text-decoration:underline}
.sims-site-nav a[aria-current="page"]{background:var(--foreground);color:var(--background)}
.sims-site-nav a.sims-methods{margin-left:auto;text-decoration:underline}
.sims-startup{padding:1rem 0}.sims-startup[hidden]{display:none}
@media(max-width:560px){.sims-site-nav a.sims-methods{margin-left:0}.sims-site-nav{font-size:13px}}
'''
CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; font-src data:; connect-src 'none'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'"

def script(source):
    return '<script>' + source.replace('</script', r'<\/script') + '</script>'

stylesheet = (SRC / 'assets/visualize.css').read_text(encoding='utf-8')
runtime = (SRC / 'page-runtime.js').read_text(encoding='utf-8')
kit = (SRC / 'assets/visualize.html').read_text(encoding='utf-8')
kit = kit.replace('<!--__INLINE_VISUALIZATION_FRAGMENT__-->', '')
vendor_license = (SRC / 'assets/FLOATING-UI-LICENSE.txt').read_text(encoding='utf-8')
for name, version in [('core', '1.7.3'), ('dom', '1.7.4')]:
    tag = f'<script src="https://unpkg.com/@floating-ui/{name}@{version}/dist/floating-ui.{name}.umd.min.js"></script>'
    if kit.count(tag) != 1:
        raise ValueError('Display helper changed: ' + name)
    kit = kit.replace(tag, script('/*!\n' + vendor_license + '\n*/\n' + (SRC / f'assets/floating-ui-{name}-{version}.js').read_text(encoding='utf-8')))
# None of the SIMS models uses Lucide. Keep tooltip/tab helpers locally; do
# not request an unused remote icon library during document startup.
kit = kit.split('<script id="codex-visualization-lucide"', 1)[0]
snapshot = json.loads((SRC / 'latest-run.json').read_text(encoding='utf-8'))
DIST.mkdir(exist_ok=True)

for filename, label, model_name, latest in PAGES:
    fragment = (SRC / 'models' / (model_name + '.html')).read_text(encoding='utf-8')
    if 'data-lucide' in fragment:
        raise ValueError('New icons require a local icon runtime')
    def guarded(match):
        return script('try {\n' + match.group(1) + '\nwindow.simsPage.ready();\n} catch(error) { window.simsPage.failed(error); }')
    fragment, script_count = re.subn(r'<script>([\s\S]*?)</script>', guarded, fragment)
    if script_count != 1:
        raise ValueError('Expected exactly one model script')
    links = ''.join(f'<a href="./{target}"' + (' aria-current="page"' if target == filename else '') + f'>{escape(title)}</a>' for target, title, _, _ in PAGES)
    nav = f'<nav class="sims-site-nav" aria-label="SIMS models"><div class="sims-brand"><strong>SIMS</strong><span>Evidence lab</span></div><div class="sims-links">{links}<a class="sims-methods" href="{REPO}/METHODS.md" target="_blank" rel="noopener noreferrer">Methods</a><a href="{REPO}" target="_blank" rel="noopener noreferrer">Source</a></div></nav>'
    seed = json.dumps(snapshot if latest else None, separators=(',', ':')).replace('<', r'\u003c')
    content = f'''<!doctype html>
<html lang="en" data-visualize-standalone data-sims-host="direct-v2">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<title>SIMS — {escape(label)}</title>
<style>{stylesheet}\n{STYLE}</style>
</head>
<body>
{nav}
<div id="sims-startup-status" class="sims-startup" role="status">Loading SIMS…</div>
<noscript>Enable JavaScript to use the SIMS model controls.</noscript>
<main id="sims-model" aria-busy="true">
<script id="sims-initial-state" type="application/json">{seed}</script>
{script(runtime)}
{fragment}
</main>
{kit}
</body></html>
'''
    (DIST / filename).write_text(content, encoding='utf-8', newline='\n')
(DIST / 'latest-run.html').write_bytes((DIST / 'index.html').read_bytes())
print('Built six self-contained SIMS pages; no iframe or remote script is needed to start.')
