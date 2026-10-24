"""Retain an audit notice when rebuilding this historical report."""
from pathlib import Path
import html,re
def apply_notice(root):
    root=Path(root);text=(root/'AUDIT_NOTICE.md').read_text(encoding='utf-8').strip()
    for name in ('README.md','report.html'):
        p=root/name
        if not p.exists():continue
        s=p.read_text(encoding='utf-8')
        s=re.sub(r'<!-- chain-audit:start -->.*?<!-- chain-audit:end -->\s*','',s,flags=re.S)
        if name.endswith('.md'):
            notice='<!-- chain-audit:start -->\n'+text+'\n<!-- chain-audit:end -->\n\n'
            lines=s.splitlines(keepends=True);s=lines[0]+'\n'+notice+''.join(lines[1:]).lstrip('\n')
        else:
            rendered=html.escape(text)
            rendered=re.sub(r'\[([^\]]+)\]\((https://[^)]+)\)',r'<a href="\2">\1</a>',rendered)
            notice='<!-- chain-audit:start --><aside style="padding:18px;border:2px solid #236574;background:#eef7f6;margin:24px 0"><p>'+rendered+'</p></aside><!-- chain-audit:end -->'
            s,n=re.subn(r'(<main(?:\s[^>]*)?>)',lambda m:m[1]+notice,s,count=1)
            if not n:s=s.replace('<body>','<body>'+notice,1)
        p.write_text(s,encoding='utf-8')
