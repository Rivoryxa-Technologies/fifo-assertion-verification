# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('runner',Path(__file__).resolve().parents[1]/'tools/run.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
class Classification(unittest.TestCase):
    def test_timeout_is_not_expected_failure(self):
        self.assertFalse(runner.accepted({'exit':-9,'timeout':True,'output':'WRITE_POINTER_FAILED'},'WRITE_POINTER_FAILED'))
    def test_wrong_or_multiple_diagnostics_rejected(self):
        for text in ('OTHER_FAILED','WRITE_POINTER_FAILED OTHER_FAILED','WRITE_POINTER_FAILED FIFO_ASSERTIONS_PASS'):
            self.assertFalse(runner.accepted({'exit':1,'timeout':False,'output':text},'WRITE_POINTER_FAILED'))
    def test_missing_executable(self):
        result=runner.execute(['/nonexistent/rivoryxa-simulator'],Path('/tmp'),1)
        self.assertFalse(runner.accepted(result,'WRITE_POINTER_FAILED'))
    def test_pass_needs_exercised_conditions(self):
        self.assertFalse(runner.accepted({'exit':0,'timeout':False,'output':'FIFO_ASSERTIONS_PASS'},None))
if __name__=='__main__': unittest.main()
