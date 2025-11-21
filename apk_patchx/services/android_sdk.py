"""Android SDK management service."""
import os
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from ..exceptions import NetworkError, ToolNotFoundError
from ..utils.core import run_command, get_apkpatchx_home, download_file


class AndroidSDKService:
    """Service for managing Android SDK components."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.sdk_root = get_apkpatchx_home() / "tools" / "sdk"
        self.cmdline_tools_dir = get_apkpatchx_home() / "tools" / "cmdline-tools"

    def ensure_java(self) -> None:
        """Ensure Java is available."""
        try:
            result = subprocess.run(["java", "-version"],
                                  capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise ToolNotFoundError(
                    "Java is required but not found. Please install Java 8 or later."
                )
        except FileNotFoundError:
            raise ToolNotFoundError(
                "Java is required but not found. Please install Java 8 or later."
            )

    def ensure_cmdline_tools(self) -> None:
        """Ensure Android command line tools are installed."""
        if (self.cmdline_tools_dir / "bin" / "sdkmanager").exists():
            return

        self.cmdline_tools_dir.mkdir(parents=True, exist_ok=True)

        tools_url = "https://dl.google.com/android/repository/commandlinetools-linux-9123335_latest.zip"
        zip_path = get_apkpatchx_home() / "tools" / "commandlinetools.zip"

        if self.verbose:
            print(f"Downloading Android command line tools...")

        download_file(tools_url, zip_path)


        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(get_apkpatchx_home() / "tools")

        zip_path.unlink()
        import stat

        cmdline_bin = self.cmdline_tools_dir / "bin"
        for f in cmdline_bin.iterdir():
            f.chmod(f.stat().st_mode | stat.S_IEXEC)

        if self.verbose:
            print("Android command line tools installed")

    def ensure_build_tools(self, version: str = "33.0.1") -> None:
        """Ensure Android build tools are installed."""
        build_tools_dir = self.sdk_root / "build-tools" / version
        if build_tools_dir.exists():
            return

        self.ensure_cmdline_tools()
        self.sdk_root.mkdir(parents=True, exist_ok=True)

        sdkmanager = self.cmdline_tools_dir / "bin" / "sdkmanager"

        if self.verbose:
            print(f"Installing build-tools {version}...")

        cmd = [
            str(sdkmanager),
            f"build-tools;{version}",
            f"--sdk_root={self.sdk_root}"
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if not self.verbose else None,
            stderr=subprocess.PIPE if not self.verbose else None,
            text=True
        )

        stdout, stderr = process.communicate(input="y\n" * 10)

        if process.returncode != 0:
            raise ToolNotFoundError(f"Failed to install build-tools: {stderr}")

        if self.verbose:
            print(f"Build-tools {version} installed")

    def ensure_platform_tools(self) -> None:
        """Ensure Android platform tools are installed."""
        platform_tools_dir = self.sdk_root / "platform-tools"
        if platform_tools_dir.exists():
            return

        self.ensure_cmdline_tools()
        self.sdk_root.mkdir(parents=True, exist_ok=True)

        sdkmanager = self.cmdline_tools_dir / "bin" / "sdkmanager"

        if self.verbose:
            print("Installing platform-tools...")

        cmd = [
            str(sdkmanager),
            "platform-tools",
            f"--sdk_root={self.sdk_root}"
        ]

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE if not self.verbose else None,
            stderr=subprocess.PIPE if not self.verbose else None,
            text=True
        )

        stdout, stderr = process.communicate(input="y\n" * 10)

        if process.returncode != 0:
            raise ToolNotFoundError(f"Failed to install platform-tools: {stderr}")

        if self.verbose:
            print("Platform-tools installed")

    def get_tool_path(self, tool: str) -> Path:
        """Get path to SDK tool."""
        if tool in ["aapt", "aapt2", "zipalign", "apksigner"]:
            self.ensure_build_tools()
            return self.sdk_root / "build-tools" / "33.0.1" / tool
        elif tool == "adb":
            self.ensure_platform_tools()
            return self.sdk_root / "platform-tools" / tool
        else:
            raise ValueError(f"Unknown tool: {tool}")
