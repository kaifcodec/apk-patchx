"""Version management utilities."""

import requests
from typing import Optional

from ..exceptions import NetworkError


def get_latest_github_release(owner: str, repo: str) -> str:
    """Get the latest release version from GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        data = response.json()
        tag_name = data.get("tag_name", "")

        if tag_name.startswith("v"):
            tag_name = tag_name[1:]

        return tag_name

    except requests.RequestException as e:
        raise NetworkError(f"Failed to get latest release for {owner}/{repo}: {e}")
    except KeyError:
        raise NetworkError(f"Invalid response format from GitHub API")


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings.

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    def version_tuple(v):
        return tuple(map(int, v.split('.')))

    try:
        v1_tuple = version_tuple(version1)
        v2_tuple = version_tuple(version2)

        if v1_tuple < v2_tuple:
            return -1
        elif v1_tuple > v2_tuple:
            return 1
        else:
            return 0
    except ValueError:

        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


def is_version_newer(current: str, latest: str) -> bool:
    """Check if latest version is newer than current."""
    return compare_versions(current, latest) < 0
