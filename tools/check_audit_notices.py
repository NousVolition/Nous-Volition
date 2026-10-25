"""Check the 13 explicit entry points and their reviewed notice/render envelopes.
Whole-file hashes deliberately require review of CSS, script or layout changes;
a substring or hidden comment is never accepted as a visible notice.
"""
from pathlib import Path
import hashlib,json,re,sys
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/"studies/community-chain-audit"
BASELINE_SHA="3586a0078346594320335045ac83196a822062fd36e7f1e64ab70c0858a053e9"
class Text(HTMLParser):
 def __init__(self):
  super().__init__();self.stack=[];self.text=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs);style=re.sub(r"\s+","",attrs.get("style","").lower())
  hidden=tag in ("script","style","template","head") or "hidden" in attrs or attrs.get("aria-hidden")=="true" or any(x in style for x in ("display:none","visibility:hidden","opacity:0"))
  if tag not in ("br","hr","img","meta","link","input"):self.stack.append((tag,hidden or any(x[1] for x in self.stack)))
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):
  if not any(x[1] for x in self.stack):self.text.append(data)
def normalized_visible(s):
 parser=Text();parser.feed(s)
 return " ".join(" ".join(parser.text).split())
def check(root=ROOT):
 root=Path(root);base=root/"studies/community-chain-audit/notice_baseline.json"
 if not base.is_file() or hashlib.sha256(base.read_bytes()).hexdigest()!=BASELINE_SHA:
  return ["Missing or changed reviewed notice baseline"]
 records=json.loads(base.read_text(encoding="utf-8"));errors=[]
 if len(records)!=13:return ["Expected 13 reviewed notice records"]
 for row in records:
  for entry in row["files"]:
   p=root/entry["path"]
   if not p.is_file():errors.append("Missing required entry point: "+entry["path"]);continue
   data=p.read_bytes();s=data.decode("utf-8")
   if hashlib.sha256(data).hexdigest()!=entry["sha256"]:
    errors.append("Notice/render envelope changed; review required: "+entry["path"])
   blocks=re.findall(r"<!-- chain-audit:start -->(.*?)<!-- chain-audit:end -->",s,re.S)
   if len(blocks)!=1 or blocks[0].strip()!=entry["notice"]:
    errors.append("Missing or changed substantive notice: "+entry["path"])
   if p.suffix==".html":
    required=normalized_visible(entry["notice"])
    if not required or required not in normalized_visible(s):
     errors.append("Notice not exposed as document text: "+entry["path"])
 return errors
def main():
 errors=check()
 if errors:
  print("\n".join(errors));return 1
 print("13 audited entry points; 26 required README/report files retain their reviewed notices and render envelopes.")
 print("No study is classified as corpus from keyword absence. See inheritance_review.json.")
 return 0
if __name__=="__main__":sys.exit(main())
