"""Real CLI regressions for the parent import/launch attack; no solver mocks."""
import sys
if __name__ == "__main__" and (not (sys.flags.isolated and sys.flags.no_site) or sys.flags.optimize):
    raise SystemExit("Use non-optimized python -I -S test_parent_launch.py -v")
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import py_compile
import shutil
import subprocess
import tempfile
import unittest
import venv

P = Path(__file__).resolve().parent

class ParentLaunch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="parent-launch-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.clone = self.root/"source"
        shutil.copytree(P,self.clone,ignore=shutil.ignore_patterns(
            "__pycache__","gate_evidence","freshness_evidence","parent_launch_evidence"))
        self.out = self.root/"output"
        self.marker = self.root/"injected-code-executed"
        self.source_hashes = {n:self.digest(self.clone/n) for n in
                              ("gated_run.py","run_manifest.py","gate_worker.py")}
    @staticmethod
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def invoke(self, flags=("-I","-S","-B"), cwd=None, env=None, help_only=False, executable=None):
        args = ["--help"] if help_only else [str(self.clone/"run_manifest.example.json"),"--output",str(self.out)]
        return subprocess.run([executable or sys.executable,*flags,str(self.clone/"gated_run.py"),*args],
                              cwd=cwd or self.clone,env=env,capture_output=True,text=True)
    def assert_rejected(self,result,reason):
        self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn(reason,result.stdout+result.stderr)
        self.assertFalse(self.out.exists())
        self.assertFalse(self.marker.exists(),"Injected Python code executed")
    def marker_code(self):
        return "from pathlib import Path\nPath("+repr(str(self.marker))+").write_text('injected')\n"
    def assert_sources_unchanged(self):
        self.assertEqual(self.source_hashes,{n:self.digest(self.clone/n) for n in self.source_hashes})
        pins=json.loads((P/"manifest_sha256.json").read_bytes())
        self.assertEqual(len(pins),86)
        for name,digest in pins.items():
            self.assertEqual(self.digest(self.clone/name),digest,name)
            self.assertEqual(self.digest(P/name),digest,name)

    def test_old_unisolated_commands_refused_before_local_import(self):
        (self.clone/"subprocess.py").write_text(self.marker_code(),encoding="utf-8")
        for flags in ((),("-I",),("-S",),("-I","-S","-O")):
            with self.subTest(flags=flags):
                self.assert_rejected(self.invoke(flags),"Gate refused")
        self.assert_sources_unchanged()

    def test_exact_fake_subprocess_launch_and_old_result_attack(self):
        # This is the previously successful attack: intercept subprocess.run,
        # reuse a genuine completed bundle, and rebind its identity/digests.
        old=self.root/"old-run";old.mkdir()
        evidence=P/"freshness_evidence"
        for name in ("results.json","test_log.txt","runner_started.json","execution_trace.json","worker_completion.json"):
            shutil.copyfile(evidence/name,old/name)
        payload = self.marker_code()+"""
import hashlib,json
STDOUT=-2
def run(command,input=None,cwd=None,env=None,stdout=None,stderr=None):
    output=Path(cwd).parent
    old=Path(OLD_PATH)
    context=json.loads((output/"run_context.json").read_text(encoding="utf-8"))
    def read(p):return json.loads(p.read_text(encoding="utf-8"))
    def save(p,d):p.write_text(json.dumps(d,indent=2)+"\\n",encoding="utf-8")
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    for name in ("results.json","test_log.txt"):
        (output/"audit-copy"/name).write_bytes((old/name).read_bytes())
    for name in ("runner_started.json","execution_trace.json","worker_completion.json"):
        data=read(old/name);data["run_nonce"]=context["run_nonce"]
        data["worker_sha256"]=context["worker_sha256"]
        if name=="execution_trace.json":
            data["worker_startup"]=dict(isolated=True,no_site=True,safe_path=True,optimize=0)
        save(output/name,data)
    completion=read(output/"worker_completion.json")
    completion.update(trace_sha256=sha(output/"execution_trace.json"),
                      start_sha256=sha(output/"runner_started.json"),
                      declaration_sha256=context["declaration_sha256"],
                      contract_sha256=context["contract_sha256"])
    save(output/"worker_completion.json",completion)
    class Result:returncode=0
    return Result()
""".replace("OLD_PATH",repr(str(old)))
        (self.clone/"subprocess.py").write_text(payload,encoding="utf-8")
        self.assert_rejected(self.invoke(),"Local standard-library shadow refused")
        self.assert_sources_unchanged()
        self.assertEqual((old/"results.json").read_bytes(),(evidence/"results.json").read_bytes())

    def test_subprocess_package_and_sourceless_bytecode_refused(self):
        package=self.clone/"subprocess";package.mkdir()
        (package/"__init__.py").write_text(self.marker_code(),encoding="utf-8")
        self.assert_rejected(self.invoke(),"Local standard-library shadow refused")
        (package/"__init__.py").unlink();package.rmdir()
        source=self.root/"payload.py";source.write_text(self.marker_code(),encoding="utf-8")
        py_compile.compile(str(source),cfile=str(self.clone/"subprocess.pyc"),doraise=True)
        self.assert_rejected(self.invoke(),"Local standard-library shadow refused")
        self.assert_sources_unchanged()

    def test_other_standard_library_shadows_refused(self):
        for name in ("pathlib.py","hashlib.py","json.py"):
            with self.subTest(name=name):
                target=self.clone/name;target.write_text(self.marker_code(),encoding="utf-8")
                self.assert_rejected(self.invoke(),"Local standard-library shadow refused")
                target.unlink()
        self.assert_sources_unchanged()

    def test_working_directory_shadow_refused(self):
        cwd=self.root/"cwd";cwd.mkdir()
        (cwd/"subprocess.py").write_text(self.marker_code(),encoding="utf-8")
        self.assert_rejected(self.invoke(cwd=cwd),"Local standard-library shadow refused")

    def test_pythonpath_and_startup_environment_ignored(self):
        injected=self.root/"pythonpath";injected.mkdir()
        for name in ("sitecustomize.py","usercustomize.py","subprocess.py"):
            (injected/name).write_text(self.marker_code(),encoding="utf-8")
        env=os.environ.copy();env["PYTHONPATH"]=str(injected)
        env["PYTHONSTARTUP"]=str(injected/"sitecustomize.py")
        env["PYTHONOPTIMIZE"]="2";env["PYTHONHOME"]=str(self.root/"invalid-home")
        result=self.invoke(env=env,help_only=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.marker.exists());self.assertFalse(self.out.exists())

    def test_checker_package_and_unchecked_bytecode_are_not_loaded(self):
        source=self.root/"cached_payload.py";source.write_text(self.marker_code(),encoding="utf-8")
        cache=Path(importlib.util.cache_from_source(str(self.clone/"run_manifest.py")))
        cache.parent.mkdir(exist_ok=True)
        py_compile.compile(str(source),cfile=str(cache),doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        package=self.clone/"run_manifest";package.mkdir()
        (package/"__init__.py").write_text(self.marker_code(),encoding="utf-8")
        result=self.invoke(help_only=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.marker.exists());self.assert_sources_unchanged()

    def test_changed_checker_source_refused_before_execution(self):
        checker=self.clone/"run_manifest.py"
        checker.write_bytes(self.marker_code().encode("utf-8")+checker.read_bytes())
        self.assert_rejected(self.invoke(),"run_manifest.py integrity mismatch")

    def test_site_pth_and_sitecustomize_hooks_disabled(self):
        prefix=self.root/"hook-venv"
        venv.EnvBuilder(with_pip=False).create(prefix)
        executable=prefix/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        lib=prefix/("Lib/site-packages" if os.name=="nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
        lib.mkdir(parents=True,exist_ok=True)
        (lib/"sitecustomize.py").write_text(self.marker_code(),encoding="utf-8")
        (lib/"injection.pth").write_text("import pathlib; pathlib.Path("+repr(str(self.marker))+").write_text('pth')\n",encoding="utf-8")
        # Positive control proves that the fixture's startup hooks can execute.
        control=subprocess.run([str(executable),"-I","-c","pass"],capture_output=True,text=True)
        self.assertEqual(control.returncode,0,control.stderr)
        self.assertTrue(self.marker.exists())
        self.marker.unlink()
        result=self.invoke(help_only=True,executable=str(executable))
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.marker.exists());self.assertFalse(self.out.exists())

    def test_imported_run_cannot_claim_a_gated_execution(self):
        script="""
from pathlib import Path
import sys,types
p=Path(sys.argv[1])
for name in ("run_manifest","gated_run"):
    file=p/(name+".py");module=types.ModuleType(name);module.__file__=str(file);sys.modules[name]=module
    exec(compile(file.read_bytes(),str(file),"exec"),module.__dict__)
raise SystemExit(sys.modules["gated_run"].run(p/"run_manifest.example.json",sys.argv[2]))
"""
        r=subprocess.run([sys.executable,"-I","-S","-B","-c",script,str(self.clone),str(self.out)],
                         capture_output=True,text=True)
        self.assert_rejected(r,"execution requires the isolated CLI")

if __name__=="__main__":
    unittest.main()

