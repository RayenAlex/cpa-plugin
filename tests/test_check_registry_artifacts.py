import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CheckRegistryArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry_path = self.root / "registry.json"
        self.artifacts_dir = self.root / "artifacts"
        self.artifacts_dir.mkdir()
        self.url_prefix = "https://example.test/artifacts"

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, plugin_id, version, goos, goarch, body=b"artifact"):
        name = f"{plugin_id}_{version}_{goos}_{goarch}.zip"
        (self.artifacts_dir / name).write_bytes(body)
        return {
            "goos": goos,
            "goarch": goarch,
            "url": f"{self.url_prefix}/{name}",
            "sha256": hashlib.sha256(body).hexdigest(),
        }

    def release_artifact(self, plugin_id, version, goos, goarch, body=b"release"):
        name = f"{plugin_id}_{version}_{goos}_{goarch}.zip"
        return {
            "goos": goos,
            "goarch": goarch,
            "url": (
                f"https://github.com/example/{plugin_id}/releases/download/"
                f"v{version}/{name}"
            ),
            "sha256": hashlib.sha256(body).hexdigest(),
        }

    def missing_artifact(self, plugin_id, version, goos, goarch):
        name = f"{plugin_id}_{version}_{goos}_{goarch}.zip"
        return {
            "goos": goos,
            "goarch": goarch,
            "url": f"{self.url_prefix}/{name}",
            "sha256": "a" * 64,
        }

    def write_registry(self, plugins):
        self.registry_path.write_text(
            json.dumps({"schema_version": 2, "plugins": plugins}),
            encoding="utf-8",
        )

    def plugin(self, plugin_id, version, artifacts, repository=None):
        plugin = {
            "id": plugin_id,
            "version": version,
            "install": {"type": "direct", "artifacts": artifacts},
        }
        if repository is not None:
            plugin["repository"] = repository
        return plugin

    def run_checker(self):
        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parents[1] / "scripts" / "check-registry-artifacts.py"),
                str(self.registry_path),
                "--artifacts-dir",
                str(self.artifacts_dir),
                "--url-prefix",
                self.url_prefix,
            ],
            capture_output=True,
            text=True,
        )

    def test_accepts_release_and_store_hosted_artifacts(self):
        quota_artifacts = [
            self.release_artifact("quota-center", "0.2.1", "darwin", "arm64"),
            self.release_artifact("quota-center", "0.2.1", "linux", "amd64"),
        ]
        store_artifacts = [
            self.artifact("store-plugin", "0.1.1", "linux", "amd64", b"store"),
        ]
        self.write_registry(
            [
                self.plugin(
                    "quota-center",
                    "0.2.1",
                    quota_artifacts,
                    repository="https://github.com/example/quota-center",
                ),
                self.plugin("store-plugin", "0.1.1", store_artifacts),
            ]
        )

        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 plugin(s), 3 artifact(s)", result.stdout)

    def test_rejects_release_url_with_wrong_version_or_filename(self):
        artifact = self.release_artifact("quota-center", "0.2.1", "darwin", "arm64")
        artifact["url"] = artifact["url"].replace("/v0.2.1/", "/v0.2.0/")
        self.write_registry(
            [
                self.plugin(
                    "quota-center",
                    "0.2.1",
                    [artifact],
                    repository="https://github.com/example/quota-center",
                )
            ]
        )

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release URL mismatch", result.stderr)

    def test_rejects_missing_store_hosted_artifact(self):
        missing_store = self.missing_artifact("store-plugin", "0.1.1", "linux", "amd64")
        self.write_registry([self.plugin("store-plugin", "0.1.1", [missing_store])])

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("store-plugin", result.stderr)
        self.assertIn("missing artifact", result.stderr)

    def test_rejects_checksum_mismatch_for_store_hosted_artifact(self):
        artifact = self.artifact("store-plugin", "0.1.1", "linux", "amd64", b"store")
        artifact["sha256"] = "b" * 64
        self.write_registry([self.plugin("store-plugin", "0.1.1", [artifact])])

        result = self.run_checker()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("store-plugin", result.stderr)
        self.assertIn("sha256 mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
