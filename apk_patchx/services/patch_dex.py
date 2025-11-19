"""Service for direct DEX patching."""

import subprocess
from pathlib import Path
from typing import Optional

from ..exceptions import FridaPatchError, ToolNotFoundError
from ..utils.core import run_command, get_apkpatchx_home, download_file


class DexPatcher:
    """Service for direct DEX file patching using dexpatch."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._dexpatch_path: Optional[Path] = None

    @property
    def dexpatch_path(self) -> Path:
        """Get dexpatch JAR path."""
        if self._dexpatch_path is None:
            self._ensure_dexpatch()
        return self._dexpatch_path

    def _ensure_dexpatch(self) -> None:
        """Ensure dexpatch is available."""
        tools_dir = get_apkpatchx_home() / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        dexpatch_path = tools_dir / "dexpatch-0.1.jar"

        if dexpatch_path.exists():
            self._dexpatch_path = dexpatch_path
            return

        # Download dexpatch
        if self.verbose:
            print("Downloading dexpatch...")

        dexpatch_url = "https://github.com/ax/DEXPatch/releases/download/v0.1/dexpatch-0.1.jar"
        download_file(dexpatch_url, dexpatch_path)

        self._dexpatch_path = dexpatch_path

        if self.verbose:
            print("Downloaded dexpatch")

    def patch_dex_file(self, dex_path: Path, target_class: str, 
                      library_name: str = "frida-gadget") -> Path:
        """Patch DEX file with loadLibrary call.

        Args:
            dex_path: Path to DEX file
            target_class: Target class name (e.g. com/example/MainActivity)
            library_name: Library name to load

        Returns:
            Path to patched DEX file
        """
        if not dex_path.exists():
            raise FridaPatchError(f"DEX file not found: {dex_path}")

        output_path = dex_path.parent / f"{dex_path.stem}.patched{dex_path.suffix}"

        cmd = [
            "java", "-jar", str(self.dexpatch_path),
            str(dex_path),
            str(output_path),
            target_class
        ]

        if self.verbose:
            print(f"Patching {dex_path} with dexpatch...")

        result = run_command(cmd)
        if result.returncode != 0:
            raise FridaPatchError(f"Failed to patch DEX file: {dex_path}")

        return output_path

    def find_dex_with_class(self, decode_dir: Path, class_name: str) -> Optional[Path]:
        """Find DEX file containing the specified class."""
        # Convert class name to internal format
        internal_name = class_name.replace(".", "/")

        # Search in classes*.dex files
        for dex_file in decode_dir.glob("classes*.dex"):
            try:
                # Use strings command to search for class in DEX
                result = subprocess.run(
                    ["strings", str(dex_file)],
                    capture_output=True, text=True, check=False
                )

                if result.returncode == 0 and internal_name in result.stdout:
                    return dex_file
            except FileNotFoundError:
                # strings command not available
                pass

        return None

    def is_dex_patched(self, dex_path: Path, library_name: str = "frida-gadget") -> bool:
        """Check if DEX file is already patched."""
        if not dex_path.exists():
            return False

        try:
            result = subprocess.run(
                ["strings", str(dex_path)],
                capture_output=True, text=True, check=False
            )

            return (result.returncode == 0 and 
                    library_name in result.stdout and
                    "loadLibrary" in result.stdout)
        except FileNotFoundError:
            # If strings is not available, assume not patched
            return False
