"""Run scientific unit tests and all aggregate reproducibility checks."""
from pathlib import Path
import datetime, json, platform, unittest
import numpy, scipy
import verify_saved

root = Path(__file__).parent
suite = unittest.defaultTestLoader.discover(str(root), pattern='test_record_tests.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
receipt = {'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'tests_run': result.testsRun,
           'failures': len(result.failures), 'errors': len(result.errors), 'passed': result.wasSuccessful(),
           'python': platform.python_version(), 'numpy': numpy.__version__, 'scipy': scipy.__version__}
if not result.wasSuccessful():
    raise SystemExit(1)
verify_saved.main()
(root / 'results/run_checks.json').write_text(json.dumps(receipt, indent=2))
