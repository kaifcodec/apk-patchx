"""Core utility functions for APKPatchx."""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional
import requests
from tqdm import tqdm

from ..exceptions import NetworkError


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(levelname)s: %(message)s'
    )


def get_apkpatchx_home() -> Path:
    """Get APKPatchx home directory."""
    return Path.home() / ".apkpatchx"


def run_command(cmd, capture_output: bool = False, text: bool = True, **kwargs):
    """Run command with proper error handling."""
    try:
        return subprocess.run(cmd, capture_output=capture_output, text=text, **kwargs)
    except FileNotFoundError as e:
        from ..exceptions import ToolNotFoundError
        raise ToolNotFoundError(f"Command not found: {cmd[0]}")


def download_file(url: str, output_path: Path, chunk_size: int = 8192) -> None:
    """Download file with progress bar."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(output_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=output_path.name) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

    except requests.RequestException as e:
        raise NetworkError(f"Failed to download {url}: {e}")
    except Exception as e:
        raise NetworkError(f"Download error: {e}")


def is_java_available() -> bool:
    """Check if Java is available."""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def validate_package_name(package_name: str) -> bool:
    """Validate Android package name format."""
    import re
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$'
    return bool(re.match(pattern, package_name))


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists and return path."""
    path.mkdir(parents=True, exist_ok=True)
    return path
