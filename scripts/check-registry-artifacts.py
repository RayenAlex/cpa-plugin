#!/usr/bin/env python3
"""Validate direct-install artifact metadata for local and GitHub Release assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("registry", type=Path)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--url-prefix", required=True)
    return parser.parse_args()


def fail(message: str) -> None:
    raise SystemExit(message)


def expected_archive_name(plugin_id: str, version: str, goos: str, goarch: str) -> str:
    values = (plugin_id, version, goos, goarch)
    if any(not value or "/" in value or "\\" in value for value in values):
        fail("plugin id, version, goos, and goarch must be non-empty path-safe values")
    return f"{plugin_id}_{version}_{goos}_{goarch}.zip"


def release_url(repository: str, version: str, archive_name: str) -> str:
    return f"{repository.rstrip('/')}/releases/download/v{version}/{archive_name}"


def verify_release_artifact(
    plugin_id: str,
    platform: str,
    repository: str,
    version: str,
    artifact: dict,
    archive_name: str,
) -> None:
    expected_url = release_url(repository, version, archive_name)
    if artifact.get("url") != expected_url:
        fail(
            f"{plugin_id} {platform}: release URL mismatch: "
            f"{artifact.get('url')!r}"
        )
    digest = str(artifact.get("sha256", "")).strip().lower()
    if not SHA256.fullmatch(digest):
        fail(f"{plugin_id} {platform}: invalid release sha256")


def verify_store_artifact(
    plugin_id: str,
    platform: str,
    artifact: dict,
    archive_name: str,
    artifacts_dir: Path,
    url_prefix: str,
) -> None:
    expected_url = f"{url_prefix}/{archive_name}"
    if artifact.get("url") != expected_url:
        fail(f"{plugin_id} {platform}: URL mismatch: {artifact.get('url')!r}")
    archive = artifacts_dir / archive_name
    if archive.parent != artifacts_dir or not archive.is_file():
        fail(f"{plugin_id} {platform}: missing artifact: {archive}")
    expected_digest = str(artifact.get("sha256", "")).strip().lower()
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_digest:
        fail(
            f"{plugin_id} {platform}: sha256 mismatch: "
            f"expected {expected_digest}, got {digest}"
        )


def main() -> int:
    args = parse_args()
    try:
        registry = json.loads(args.registry.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(str(error))

    plugins = registry.get("plugins")
    if not isinstance(plugins, list):
        fail("plugins must be an array")
    artifacts_dir = args.artifacts_dir.resolve()
    url_prefix = args.url_prefix.rstrip("/")
    artifact_count = 0
    for plugin_index, plugin in enumerate(plugins):
        if not isinstance(plugin, dict):
            fail(f"plugins[{plugin_index}] must be an object")
        plugin_id = str(plugin.get("id", "")).strip()
        version = str(plugin.get("version", "")).strip()
        repository = str(plugin.get("repository", "")).strip().rstrip("/")
        artifacts = (plugin.get("install") or {}).get("artifacts") or []
        if not isinstance(artifacts, list) or not artifacts:
            fail(f"plugins[{plugin_index}] {plugin_id!r}: missing direct-install artifacts")
        for artifact_index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                fail(f"plugins[{plugin_index}].install.artifacts[{artifact_index}] must be an object")
            goos = str(artifact.get("goos", "")).strip()
            goarch = str(artifact.get("goarch", "")).strip()
            archive_name = expected_archive_name(plugin_id, version, goos, goarch)
            platform = f"{goos}/{goarch}"
            expected_release_prefix = f"{repository}/releases/download/" if repository else ""
            if expected_release_prefix and str(artifact.get("url", "")).startswith(
                expected_release_prefix
            ):
                verify_release_artifact(
                    plugin_id,
                    platform,
                    repository,
                    version,
                    artifact,
                    archive_name,
                )
            else:
                verify_store_artifact(
                    plugin_id,
                    platform,
                    artifact,
                    archive_name,
                    artifacts_dir,
                    url_prefix,
                )
            artifact_count += 1

    print(f"OK {args.registry}: {len(plugins)} plugin(s), {artifact_count} artifact(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
