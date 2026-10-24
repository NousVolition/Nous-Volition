from pathlib import Path
import html
D=Path(__file__).resolve().parent
readme=(D/"README.md").read_text(encoding="utf-8")
# Small dependency-free renderer for this report; preserve tables, links and code.
def inline(s):
 s=html.escape(s);s=__import__('re').sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
 s=__import__('re').sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s);s=__import__('re').sub(r'`([^`]+)`',r'<code>\1</code>',s);return s
parts=[];code=[];intable=False;incode=False;inlist=False
for line in readme.splitlines():
 if line.startswith('```'):
  if incode:parts.append('<pre>'+html.escape('\n'.join(code))+'</pre>');code=[]
  incode=not incode;continue
 if incode:code.append(line);continue
 if line.startswith('|'):
  if not intable:parts.append('<div class="scroll"><table>');intable=True
  if not set(line.replace('|','').replace(':','').replace(' ',''))<={'-'}:parts.append('<tr>'+''.join('<td>'+inline(c.strip())+'</td>' for c in line.strip('|').split('|'))+'</tr>')
  continue
 if intable:parts.append('</table></div>');intable=False
 if line.startswith('- '):
  if not inlist:parts.append('<ul>');inlist=True
  parts.append('<li>'+inline(line[2:])+'</li>');continue
 if inlist:parts.append('</ul>');inlist=False
 if line.startswith('#'):level=len(line)-len(line.lstrip('#'));parts.append(f'<h{level}>'+inline(line[level:].strip())+f'</h{level}>')
 elif line.strip():parts.append('<p>'+inline(line)+'</p>')
style='body{max-width:1100px;margin:36px auto;padding:0 24px;font:17px/1.65 system-ui;color:#20363d;background:#fcfcf9}h1{font-size:38px;line-height:1.15}h2{margin-top:36px;color:#165b68}a{color:#096d82}li{margin:12px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%}td{padding:10px;border-bottom:1px solid #ccd6d6}tr:first-child{font-weight:bold;background:#eaf1ef}pre{padding:20px;background:#eaf1ef;overflow:auto}code{font-size:.88em}'
(D/'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Source-chain audit — Streams and Rocks</title><style>'+style+'</style><main>'+''.join(parts)+'</main></html>',encoding='utf-8')
