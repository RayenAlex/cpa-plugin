#!/usr/bin/env python3
"""Synchronize cpa-quota-warmup direct-install metadata from GitHub Releases."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

PLUGIN_ID = "cpa-quota-warmup"
REPOSITORY = "https://github.com/szxypi/cpa-quota-warmup"
LATEST_RELEASE_URL = "https://api.github.com/repos/szxypi/cpa-quota-warmup/releases/latest"
SUPPORTED_PLATFORMS = (("linux", "amd64"), ("linux", "arm64"))
VERSION_PATTERN = re.compile(r"^[0-9][0-9A-Za-z.+-]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def release_version(tag_name: object) -> str:
    tag = str(tag_name or "").strip()
    if tag.startswith(("v", "V")):
        tag = tag[1:]
    if not VERSION_PATTERN.fullmatch(tag):
        raise ValueError(f"invalid release tag {tag_name!r}")
    return tag


def release_archive_url(version: str, goos: str, goarch: str) -> str:
    archive = f"{PLUGIN_ID}_{version}_{goos}_{goarch}.zip"
    return f"{REPOSITORY}/releases/download/v{version}/{archive}"


def sha256_from_asset(asset: dict[str, Any]) -> str | None:
    digest = str(asset.get("digest", "")).strip().lower()
    if not digest.startswith("sha256:"):
        return None
    sha256 = digest.removeprefix("sha256:")
    return sha256 if SHA256_PATTERN.fullmatch(sha256) else None


def download_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "cpa-plugin-sync"})
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except (HTTPError, URLError) as error:
        raise RuntimeError(f"download {url}: {error}") from error


def release_artifacts(release: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    version = release_version(release.get("tag_name"))
    assets = {
        str(asset.get("name", "")): asset
        for asset in release.get("assets", [])
        if isinstance(asset, dict)
    }
    artifacts: list[dict[str, str]] = []

    for goos, goarch in SUPPORTED_PLATFORMS:
        archive_name = f"{PLUGIN_ID}_{version}_{goos}_{goarch}.zip"
        asset = assets.get(archive_name)
        if asset is None:
            raise ValueError(f"release v{version} is missing {goos}/{goarch} archive")

        expected_url = release_archive_url(version, goos, goarch)
        actual_url = str(asset.get("browser_download_url", "")).strip()
        if actual_url != expected_url:
            raise ValueError(
                f"release v{version} {goos}/{goarch} URL mismatch: {actual_url!r}"
            )

        sha256 = sha256_from_asset(asset)
        if sha256 is None:
            sha256 = hashlib.sha256(download_bytes(actual_url)).hexdigest()

        artifacts.append(
            {
                "goos": goos,
                "goarch": goarch,
                "url": expected_url,
                "sha256": sha256,
            }
        )

    return version, artifacts


def update_registry(
    registry: dict[str, Any], version: str, artifacts: list[dict[str, str]]
) -> bool:
    for plugin in registry.get("plugins", []):
        if plugin.get("id") != PLUGIN_ID:
            continue

        updated_install = {"type": "direct", "artifacts": artifacts}
        changed = (
            plugin.get("version") != version or plugin.get("install") != updated_install
        )
        plugin["version"] = version
        plugin["install"] = updated_install
        return changed

    raise ValueError(f"registry does not contain {PLUGIN_ID!r}")


def fetch_latest_release(token: str | None) -> dict[str, Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "cpa-plugin-sync",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(LATEST_RELEASE_URL, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"fetch latest upstream release: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError("latest upstream release response is not an object")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=Path("registry.json"))
    parser.add_argument(
        "--release-json",
        type=Path,
        help="Use a saved GitHub release API response instead of a network request.",
    )
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    if args.release_json is not None:
        release = json.loads(args.release_json.read_text(encoding="utf-8"))
    else:
        release = fetch_latest_release(os.environ.get(args.token_env))

    version, artifacts = release_artifacts(release)
    changed = update_registry(registry, version, artifacts)
    if changed:
        args.registry.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Synced {PLUGIN_ID} v{version}.")
    else:
        print(f"{PLUGIN_ID} is already at v{version}.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
