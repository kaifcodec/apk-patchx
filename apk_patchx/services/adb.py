"""ADB service for device operations."""

import re
import subprocess
from pathlib import Path
from typing import List, Optional

from ..exceptions import ADBError, ToolNotFoundError
from ..utils.core import run_command, get_apkpatchx_home
from .android_sdk import AndroidSDKService


class ADBService:
    """Service for ADB operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.sdk_service = AndroidSDKService(verbose=verbose)
        self._adb_path: Optional[Path] = None

    @property
    def adb_path(self) -> Path:
        """Get ADB executable path."""
        if self._adb_path is None:

            result = subprocess.run(["which", "adb"], capture_output=True, text=True)
            if result.returncode == 0:
                self._adb_path = Path(result.stdout.strip())
            else:

                self.sdk_service.ensure_platform_tools()
                sdk_root = get_apkpatchx_home() / "tools" / "sdk"
                self._adb_path = sdk_root / "platform-tools" / "adb"

            if not self._adb_path.exists():
                raise ToolNotFoundError("ADB not found and SDK installation failed")

        return self._adb_path

    def pull_package(self, package_name: str) -> List[Path]:
        """Pull APK(s) for given package name."""

        cmd = [str(self.adb_path), "shell", "pm", "path", package_name]
        result = run_command(cmd, capture_output=True, text=True)

        if result.returncode != 0 or not result.stdout.strip():
            raise ADBError(f"Package {package_name} not found on device")

        package_paths = []
        for line in result.stdout.strip().split("\n"):
            if line.startswith("package:"):
                package_paths.append(line.replace("package:", ""))

        if not package_paths:
            raise ADBError(f"No package paths found for {package_name}")


        pulled_apks = []
        if len(package_paths) > 1:

            split_dir = Path(f"{package_name}_split_apks")
            split_dir.mkdir(exist_ok=True)

            for i, package_path in enumerate(package_paths):
                apk_name = f"split_{i}.apk" if i > 0 else "base.apk"
                local_path = split_dir / apk_name

                cmd = [str(self.adb_path), "pull", package_path, str(local_path)]
                result = run_command(cmd)
                if result.returncode != 0:
                    raise ADBError(f"Failed to pull {package_path}")

                pulled_apks.append(local_path)
        else:

            local_path = Path(f"{package_name}.apk")
            cmd = [str(self.adb_path), "pull", package_paths[0], str(local_path)]
            result = run_command(cmd)
            if result.returncode != 0:
                raise ADBError(f"Failed to pull {package_paths[0]}")

            pulled_apks.append(local_path)

        return pulled_apks

    def is_device_connected(self) -> bool:
        """Check if device is connected."""
        try:
            cmd = [str(self.adb_path), "devices"]
            result = run_command(cmd, capture_output=True, text=True)

            lines = result.stdout.strip().split("\n")[1:]
            for line in lines:
                if line.strip() and "\tdevice" in line:
                    return True
            return False
        except Exception:
            return False
