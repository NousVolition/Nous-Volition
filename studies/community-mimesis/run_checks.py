from pathlib import Path
import subprocess,sys,json,datetime,re
root=Path(__file__).parent
unit=subprocess.run([sys.executable,'-m','unittest','-q'],cwd=root,text=True,capture_output=True)
saved=subprocess.run([sys.executable,'verify_saved.py'],cwd=root,text=True,capture_output=True)
log=unit.stdout+unit.stderr+saved.stdout+saved.stderr
print(log)
(root/'results/checks.txt').write_text(log,encoding='utf-8')
m=re.search(r'Ran (\d+) tests',unit.stderr)
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'unit_tests':int(m.group(1)) if m else None,'unit_exit_code':unit.returncode,'saved_exit_code':saved.returncode,
        'saved_checks':json.loads(saved.stdout) if saved.returncode==0 else None,'passed':unit.returncode==saved.returncode==0}
(root/'results/checks.json').write_text(json.dumps(result,indent=2)+'\n')
if not result['passed']:sys.exit(1)
