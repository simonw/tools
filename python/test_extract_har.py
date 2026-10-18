import importlib.util
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner


SCRIPT = Path(__file__).with_name("extract_har.py")
SPEC = importlib.util.spec_from_file_location("extract_har", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExtractHarBadZipTests(unittest.TestCase):
    def test_non_zip_input_returns_a_click_error_without_traceback(self):
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "invalid.txt"
            input_path.write_text("not a zip file", encoding="utf-8")

            result = runner.invoke(
                MODULE.extract_har,
                [str(input_path), "text/plain", "--output", str(Path(directory) / "out")],
            )

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Invalid ZIP archive", result.output)
        self.assertNotIn("Traceback", result.output)


if __name__ == "__main__":
    unittest.main()
