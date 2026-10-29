import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('operation_training', Path(__file__).resolve().parents[1] / 'examples' / 'operation_training.py')
training = importlib.util.module_from_spec(spec)
spec.loader.exec_module(training)


class TrainingTests(unittest.TestCase):
    def test_isolated_generation_and_result_rejection(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / 'case'
            training.prepare(root)
            with self.assertRaises(FileExistsError):
                training.prepare(root)
            actual = Path(base) / 'actual.json'
            actual.write_text(json.dumps({'values': [0.5, 2, 3, 1], 'total': 6.5}))
            self.assertTrue(training.verify(root, 'logic', actual)['verified'])
            actual.write_text(json.dumps({'values': [2, 3, 1], 'total': 6}))
            with self.assertRaises(ValueError):
                training.verify(root, 'logic', actual)

    def test_generated_paths_stay_in_fixture_directory(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / 'case'
            training.prepare(root)
            plan = json.loads((root / 'file_wait_regex.json').read_text(encoding='utf-8'))
            paths = [Path(b['inputs']['path']) for b in plan['blocks'] if 'path' in b['inputs']]
            self.assertTrue(paths)
            self.assertTrue(all(p.parent == root.resolve() for p in paths))


if __name__ == '__main__':
    unittest.main()
