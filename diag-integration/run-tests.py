import unittest, sys
from pathlib import Path
suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful() or result.skipped or result.testsRun<116:sys.exit(1)
print('GITM_DIAGNOSTIC_TESTS_PASS|'+str(result.testsRun),flush=True)
