import json
import subprocess
import sys
import unittest
from pathlib import Path


class RegistryArtifactTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[1]
        registry = json.loads((self.root / "registry.json").read_text(encoding="utf-8"))
        self.plugins = {plugin["id"]: plugin for plugin in registry["plugins"]}

    def test_quota_center_uses_immutable_standalone_release(self):
        plugin = self.plugins["quota-center"]
        self.assertEqual(plugin["version"], "0.2.1")
        self.assertEqual(plugin["repository"], "https://github.com/RayenAlex/quota-center")
        self.assertEqual(plugin["homepage"], "https://github.com/RayenAlex/quota-center")

        expected = {
            ("darwin", "arm64"): (
                "https://github.com/RayenAlex/quota-center/releases/download/"
                "v0.2.1/quota-center_0.2.1_darwin_arm64.zip",
                "11ba4b7fd3631459bead41d1f078256b649746b34f9ce3c29d24d62760acaad0",
            ),
            ("linux", "amd64"): (
                "https://github.com/RayenAlex/quota-center/releases/download/"
                "v0.2.1/quota-center_0.2.1_linux_amd64.zip",
                "882a73af6a52721d48805bbe3f89c4702977152d54b5f86014eb8274ac72fe69",
            ),
        }
        actual = {
            (artifact["goos"], artifact["goarch"]): (
                artifact["url"],
                artifact["sha256"],
            )
            for artifact in plugin["install"]["artifacts"]
        }
        self.assertEqual(actual, expected)

    def test_quota_warmup_tracks_supported_upstream_release_artifacts(self):
        self.assertIn("cpa-quota-warmup", self.plugins)
        plugin = self.plugins["cpa-quota-warmup"]
        self.assertEqual(plugin["name"], "额度预热")
        self.assertEqual(plugin["author"], "szxypi")
        self.assertEqual(
            plugin["repository"], "https://github.com/szxypi/cpa-quota-warmup"
        )
        self.assertEqual(
            plugin["homepage"], "https://github.com/szxypi/cpa-quota-warmup"
        )
        self.assertEqual(plugin["license"], "MIT")
        self.assertRegex(plugin["version"], r"^[0-9][0-9A-Za-z.+-]*$")

        version = plugin["version"]
        expected_platforms = {("linux", "amd64"), ("linux", "arm64")}
        artifacts = plugin["install"]["artifacts"]
        self.assertEqual(
            {(artifact["goos"], artifact["goarch"]) for artifact in artifacts},
            expected_platforms,
        )
        for artifact in artifacts:
            goos = artifact["goos"]
            goarch = artifact["goarch"]
            self.assertEqual(
                artifact["url"],
                "https://github.com/szxypi/cpa-quota-warmup/releases/download/"
                f"v{version}/cpa-quota-warmup_{version}_{goos}_{goarch}.zip",
            )
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")

    def test_registry_checker_accepts_store_and_release_artifacts(self):
        result = subprocess.run(
            [
                sys.executable,
                str(self.root / "scripts" / "check-registry-artifacts.py"),
                str(self.root / "registry.json"),
                "--artifacts-dir",
                str(self.root / "artifacts"),
                "--url-prefix",
                "https://raw.githubusercontent.com/RayenAlex/cpa-plugin/main/artifacts",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("2 plugin(s), 4 artifact(s)", result.stdout)

    def test_store_contains_only_supported_standalone_plugin_entries(self):
        self.assertEqual(set(self.plugins), {"quota-center", "cpa-quota-warmup"})
        self.assertFalse((self.root / "zhipu-quota").exists())
        self.assertFalse(
            (self.root / ".github" / "workflows" / "publish-linux-amd64.yml").exists()
        )


if __name__ == "__main__":
    unittest.main()
