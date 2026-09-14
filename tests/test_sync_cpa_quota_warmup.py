import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT_PATH = ROOT / "scripts" / "sync_cpa_quota_warmup.py"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_cpa_quota_warmup", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyncCPAQuotaWarmupTest(unittest.TestCase):
    def setUp(self):
        self.sync = load_sync_module()
        self.release = {
            "tag_name": "v0.6.3",
            "assets": [
                {
                    "name": "cpa-quota-warmup_0.6.3_linux_amd64.zip",
                    "browser_download_url": (
                        "https://github.com/szxypi/cpa-quota-warmup/releases/download/"
                        "v0.6.3/cpa-quota-warmup_0.6.3_linux_amd64.zip"
                    ),
                    "digest": (
                        "sha256:0f8ae046d6d6d40b26e206f9f685ec8c6d184691dd488f468ab7ed0da5dc1a3a"
                    ),
                },
                {
                    "name": "cpa-quota-warmup_0.6.3_linux_arm64.zip",
                    "browser_download_url": (
                        "https://github.com/szxypi/cpa-quota-warmup/releases/download/"
                        "v0.6.3/cpa-quota-warmup_0.6.3_linux_arm64.zip"
                    ),
                    "digest": (
                        "sha256:1d5f2d6b7fe6617f0839d0e82c0b832110214830e9f5fdee4f772115e2f5bbf6"
                    ),
                },
            ],
        }

    def test_selects_only_supported_platform_release_archives(self):
        version, artifacts = self.sync.release_artifacts(self.release)

        self.assertEqual(version, "0.6.3")
        self.assertEqual(
            artifacts,
            [
                {
                    "goos": "linux",
                    "goarch": "amd64",
                    "url": (
                        "https://github.com/szxypi/cpa-quota-warmup/releases/download/"
                        "v0.6.3/cpa-quota-warmup_0.6.3_linux_amd64.zip"
                    ),
                    "sha256": "0f8ae046d6d6d40b26e206f9f685ec8c6d184691dd488f468ab7ed0da5dc1a3a",
                },
                {
                    "goos": "linux",
                    "goarch": "arm64",
                    "url": (
                        "https://github.com/szxypi/cpa-quota-warmup/releases/download/"
                        "v0.6.3/cpa-quota-warmup_0.6.3_linux_arm64.zip"
                    ),
                    "sha256": "1d5f2d6b7fe6617f0839d0e82c0b832110214830e9f5fdee4f772115e2f5bbf6",
                },
            ],
        )

    def test_rejects_a_release_missing_a_supported_platform_archive(self):
        self.release["assets"].pop()

        with self.assertRaisesRegex(ValueError, "linux/arm64"):
            self.sync.release_artifacts(self.release)

    def test_updates_only_the_warmup_plugin_entry(self):
        registry = {
            "schema_version": 2,
            "plugins": [
                {"id": "quota-center", "version": "0.2.1"},
                {
                    "id": "cpa-quota-warmup",
                    "version": "0.2.2",
                    "install": {"type": "direct", "artifacts": []},
                },
            ],
        }
        version, artifacts = self.sync.release_artifacts(self.release)

        changed = self.sync.update_registry(registry, version, artifacts)

        self.assertTrue(changed)
        self.assertEqual(registry["plugins"][0], {"id": "quota-center", "version": "0.2.1"})
        self.assertEqual(registry["plugins"][1]["version"], "0.6.3")
        self.assertEqual(registry["plugins"][1]["install"], {"type": "direct", "artifacts": artifacts})


if __name__ == "__main__":
    unittest.main()
