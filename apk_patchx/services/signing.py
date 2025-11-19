"""APK signing service."""

import subprocess
from pathlib import Path
from typing import Optional

from ..exceptions import SigningError, ToolNotFoundError
from ..utils.core import run_command, get_apkpatchx_home
from .android_sdk import AndroidSDKService


class SigningService:
    """Service for APK signing operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.sdk_service = AndroidSDKService(verbose=verbose)
        self._keystore_path: Optional[Path] = None

    @property
    def keystore_path(self) -> Path:
        """Get debug keystore path."""
        if self._keystore_path is None:
            keystore_path = get_apkpatchx_home() / "debug.keystore"
            if not keystore_path.exists():
                self._generate_debug_keystore(keystore_path)
            self._keystore_path = keystore_path
        return self._keystore_path

    def _generate_debug_keystore(self, keystore_path: Path) -> None:
        """Generate debug keystore."""
        if self.verbose:
            print("Generating debug keystore...")

        cmd = [
            "keytool", "-genkey", "-v",
            "-keystore", str(keystore_path),
            "-alias", "apkpatchx_debug",
            "-keyalg", "RSA",
            "-keysize", "2048",
            "-validity", "10000",
            "-storepass", "apkpatchx",
            "-keypass", "apkpatchx",
            "-dname", "CN=APKPatchx Debug, OU=Debug, O=APKPatchx, C=US",
            "-noprompt"
        ]

        result = run_command(cmd)
        if result.returncode != 0:
            raise SigningError("Failed to generate debug keystore")

    def sign_apk(self, apk_path: Path, output_path: Optional[Path] = None) -> Path:
        """Sign APK file."""
        if output_path is None:
            output_path = apk_path.parent / f"{apk_path.stem}_signed.apk"

        # First align the APK
        aligned_path = self._zipalign_apk(apk_path)

        # Then sign it
        signed_path = self._apksigner_sign(aligned_path, output_path)

        # Clean up aligned file if it's temporary
        if aligned_path != apk_path:
            aligned_path.unlink(missing_ok=True)

        return signed_path

    def _zipalign_apk(self, apk_path: Path) -> Path:
        """Align APK using zipalign."""
        zipalign = self.sdk_service.get_tool_path("zipalign")
        aligned_path = apk_path.parent / f"{apk_path.stem}_aligned.apk"

        cmd = [str(zipalign), "-p", "4", str(apk_path), str(aligned_path)]

        if self.verbose:
            print(f"Aligning {apk_path}...")

        result = run_command(cmd)
        if result.returncode != 0:
            raise SigningError(f"Failed to align APK: {apk_path}")

        return aligned_path

    def _apksigner_sign(self, apk_path: Path, output_path: Path) -> Path:
        """Sign APK using apksigner."""
        apksigner = self.sdk_service.get_tool_path("apksigner")

        cmd = [
            str(apksigner), "sign",
            "--ks", str(self.keystore_path),
            "--ks-key-alias", "apkpatchx_debug",
            "--ks-pass", "pass:apkpatchx",
            "--key-pass", "pass:apkpatchx",
            "--out", str(output_path),
            str(apk_path)
        ]

        if self.verbose:
            print(f"Signing {apk_path}...")

        result = run_command(cmd)
        if result.returncode != 0:
            raise SigningError(f"Failed to sign APK: {apk_path}")

        return output_path
