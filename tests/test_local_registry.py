import subprocess
import unittest
from pathlib import Path


class LocalRegistryTest(unittest.TestCase):
    def test_local_registry_matches_all_artifact_checksums(self):
        root = Path(__file__).parents[1]
        artifacts_dir = root / ".local-store" / "artifacts"
        if not artifacts_dir.is_dir():
            self.skipTest("local archives have not been packaged")
        result = subprocess.run(
            [
                "python3",
                str(root / "scripts" / "check-registry-artifacts.py"),
                str(root / ".local-store" / "registry.json"),
                "--artifacts-dir",
                str(artifacts_dir),
                "--url-prefix",
                "http://127.0.0.1:18080/artifacts",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 artifact(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
