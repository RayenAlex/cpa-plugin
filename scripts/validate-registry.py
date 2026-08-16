#!/usr/bin/env python3
"""Validate the third-party CLIProxyAPI plugin registry."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
VERSION = re.compile(r"^[0-9][0-9A-Za-z.+-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
URL = re.compile(r"^https?://", re.IGNORECASE)


def fail(message: str) -> None:
    raise SystemExit(message)


def validate_artifact(plugin_id: str, artifact: dict, index: int) -> None:
    goos = str(artifact.get("goos", "")).strip()
    goarch = str(artifact.get("goarch", "")).strip()
    url = str(artifact.get("url", "")).strip()
    sha256 = str(artifact.get("sha256", "")).strip().lower()
    if not goos or not goarch:
        fail(f"plugins[{plugin_id!r}].install.artifacts[{index}]: goos and goarch are required")
    if not URL.match(url):
        fail(f"plugins[{plugin_id!r}].install.artifacts[{index}].url must use HTTP or HTTPS")
    if not SHA256.fullmatch(sha256):
        fail(f"plugins[{plugin_id!r}].install.artifacts[{index}].sha256 must contain 64 hex characters")


def validate_plugin(plugin: dict, index: int) -> None:
    for field in ("id", "name", "description", "author"):
        if not str(plugin.get(field, "")).strip():
            fail(f"plugins[{index}]: missing {field}")
    plugin_id = plugin["id"].strip()
    if not PLUGIN_ID.fullmatch(plugin_id):
        fail(f"plugins[{index}]: invalid id {plugin_id!r}")
    version = str(plugin.get("version", "")).strip()
    if not version or not VERSION.fullmatch(version):
        fail(f"plugins[{index}]: invalid version {version!r}")
    install = plugin.get("install") or {}
    if str(install.get("type", "")).strip() != "direct":
        fail(f"plugins[{index}]: install.type must be direct")
    artifacts = install.get("artifacts") or []
    if not artifacts:
        fail(f"plugins[{index}]: direct install requires at least one artifact")
    seen = set()
    for artifact_index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            fail(f"plugins[{index}].install.artifacts[{artifact_index}] must be an object")
        key = (artifact.get("goos"), artifact.get("goarch"))
        if key in seen:
            fail(f"plugins[{index}].install.artifacts[{artifact_index}]: duplicate platform {key}")
        seen.add(key)
        validate_artifact(plugin_id, artifact, artifact_index)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "registry.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(str(error))
    if data.get("schema_version") != 2:
        fail("schema_version must be 2")
    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        fail("plugins must be an array")
    ids = set()
    for index, plugin in enumerate(plugins):
        if not isinstance(plugin, dict):
            fail(f"plugins[{index}] must be an object")
        validate_plugin(plugin, index)
        plugin_id = plugin["id"].strip()
        if plugin_id in ids:
            fail(f"plugins[{index}]: duplicate id {plugin_id!r}")
        ids.add(plugin_id)
    print(f"OK {path}: {len(plugins)} plugin(s), schema_version=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
