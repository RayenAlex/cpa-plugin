import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class ValidateRegistryTest(unittest.TestCase):
    def run_payload(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(data, handle)
            path = handle.name
        return subprocess.run(
            ["python3", str(Path(__file__).parents[1] / "scripts" / "validate-registry.py"), path],
            capture_output=True,
            text=True,
        )

    def valid_registry(self):
        return {
            "schema_version": 2,
            "plugins": [
                {
                    "id": "quota-center",
                    "name": "Quota Center",
                    "description": "Shows quota usage.",
                    "author": "rayen",
                    "version": "0.1.0",
                    "repository": "https://github.com/RayenAlex/quota-center",
                    "install": {
                        "type": "direct",
                        "artifacts": [
                            {
                                "goos": "darwin",
                                "goarch": "arm64",
                                "url": "https://example.test/zhipu.zip",
                                "sha256": "a" * 64,
                            }
                        ],
                    },
                }
            ],
        }

    def test_valid_schema2_direct_registry(self):
        result = self.run_payload(self.valid_registry())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_registry_rejects_bad_direct_artifact(self):
        data = self.valid_registry()
        data["plugins"][0]["install"]["artifacts"] = []
        result = self.run_payload(data)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
