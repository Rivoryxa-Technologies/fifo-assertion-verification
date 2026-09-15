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
    def test_pass_metadata_must_match_case(self):
        case=runner.CASES[0]
        good='EXERCISE scenario=0 seed=101 depth=4 width=8 writes=2 reads=2\nFIFO_ASSERTIONS_PASS'
        bad='EXERCISE scenario=0 seed=999 depth=4 width=8 writes=2 reads=2\nFIFO_ASSERTIONS_PASS'
        result=lambda text: {'exit':0,'timeout':False,'output':text}
        self.assertTrue(runner.accepted(result(good),None,case))
        self.assertFalse(runner.accepted(result(bad),None,case))
    def test_modified_source_rejected(self):
        provenance={'revision':'72d8122a7c5d458afabff2f858fe76f134010009','sha256':runner.hashlib.sha256(b'original').hexdigest()}
        self.assertTrue(runner.source_matches(b'original',provenance))
        self.assertFalse(runner.source_matches(b'changed',provenance))
    def test_complete_matrix_rejects_duplicate(self):
        cases=[{'variant':v,'case_id':case['id']} for v in runner.VARIANTS for case in runner.CASES]
        self.assertTrue(runner.complete_matrix(cases))
        cases[-1]=cases[0]
        self.assertFalse(runner.complete_matrix(cases))
    def test_targeted_failure_classification(self):
        happy=runner.CASES[0]
        boundary=next(case for case in runner.CASES if case['scenario']==1)
        self.assertIsNone(runner.expected_diagnostic('full_maxdata_pointer',happy))
        self.assertEqual(runner.expected_diagnostic('full_maxdata_pointer',boundary),'WRITE_POINTER_FAILED')
    def test_nonfatal_failure_rejected(self):
        text='FIFO_ASSERTIONS_PASS\nEXERCISE received=16 blocked_writes=16 blocked_reads=16 write_wraps=4 read_wraps=4\nWRITE_POINTER_FAILED'
        self.assertFalse(runner.accepted({'exit':0,'timeout':False,'output':text},None))
if __name__=='__main__': unittest.main()
