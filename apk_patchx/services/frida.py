"""Frida gadget injection service."""

import re
from pathlib import Path
from typing import Optional, Dict

from ..exceptions import FridaPatchError, NetworkError, ValidationError
from ..utils.core import run_command, get_apkpatchx_home, download_file
from ..utils.versions import get_latest_github_release
from .apktool import ApktoolService
from .signing import SigningService


class FridaService:
    """Service for Frida gadget operations."""

    ARCH_MAPPING = {
        "arm": ("armeabi-v7a", "android-arm"),
        "arm64": ("arm64-v8a", "android-arm64"),
        "x86": ("x86", "android-x86"),
        "x86_64": ("x86_64", "android-x86_64")
    }

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.apktool_service = ApktoolService(verbose=verbose)
        self.signing_service = SigningService(verbose=verbose)

    def patch_apk(self, apk_path: Path, arch: str, gadget_config: Optional[Path] = None,
                 add_network_config: bool = False, no_sources: bool = False,
                 only_main_classes: bool = False, frida_version: Optional[str] = None,
                 decode_args: Optional[str] = None, build_args: Optional[str] = None) -> Path:
        """Patch APK with Frida gadget."""
        if arch not in self.ARCH_MAPPING:
            raise ValidationError(f"Unsupported architecture: {arch}")

        # Get Frida gadget
        gadget_path = self._ensure_frida_gadget(arch, frida_version)

        # Decode APK
        decode_dir = self.apktool_service.decode(
            apk_path,
            no_resources=False,
            no_sources=no_sources,
            only_main_classes=only_main_classes,
            extra_args=decode_args
        )

        # Inject gadget
        self._inject_gadget(decode_dir, arch, gadget_path, gadget_config, no_sources)

        # Update manifest
        self._update_manifest(decode_dir, add_network_config)

        # Build patched APK
        output_path = apk_path.parent / f"{apk_path.stem}.gadget.apk"
        built_path = self.apktool_service.build(
            decode_dir,
            output_path,
            add_network_config=add_network_config,
            extra_args=build_args
        )

        # Sign APK
        signed_path = self.signing_service.sign_apk(built_path)

        return signed_path

    def _ensure_frida_gadget(self, arch: str, version: Optional[str] = None) -> Path:
        """Ensure Frida gadget is available for architecture."""
        if version is None:
            version = get_latest_github_release("frida", "frida")

        abi_name, frida_arch = self.ARCH_MAPPING[arch]
        gadget_name = f"frida-gadget-{version}-{frida_arch}.so"
        gadget_xz_name = f"{gadget_name}.xz"

        tools_dir = get_apkpatchx_home() / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        gadget_path = tools_dir / gadget_name
        gadget_xz_path = tools_dir / gadget_xz_name

        # Check if already downloaded and extracted
        if gadget_path.exists():
            return gadget_path

        # Download if needed
        if not gadget_xz_path.exists():
            if self.verbose:
                print(f"Downloading Frida gadget {version} for {arch}...")

            gadget_url = f"https://github.com/frida/frida/releases/download/{version}/{gadget_xz_name}"
            download_file(gadget_url, gadget_xz_path)

        # Extract XZ file
        if self.verbose:
            print(f"Extracting {gadget_xz_name}...")

        try:
            import lzma
            with lzma.open(gadget_xz_path, 'rb') as xz_file:
                with open(gadget_path, 'wb') as out_file:
                    out_file.write(xz_file.read())
        except ImportError:
            # Fallback to system unxz
            cmd = ["unxz", str(gadget_xz_path)]
            result = run_command(cmd)
            if result.returncode != 0:
                raise FridaPatchError("Failed to extract Frida gadget (unxz not found)")

        return gadget_path

    def _inject_gadget(self, decode_dir: Path, arch: str, gadget_path: Path,
                      gadget_config: Optional[Path] = None, no_sources: bool = False) -> None:
        """Inject Frida gadget into decoded APK."""
        abi_name, _ = self.ARCH_MAPPING[arch]

        # Create lib directory and copy gadget
        lib_dir = decode_dir / "lib" / abi_name
        lib_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy2(gadget_path, lib_dir / "libfrida-gadget.so")

        # Copy gadget config if provided
        if gadget_config:
            shutil.copy2(gadget_config, lib_dir / "libfrida-gadget.config.so")

        if not no_sources:
            # Inject loadLibrary call into smali
            self._inject_load_library_smali(decode_dir)
        else:
            # Use dexpatch for direct DEX patching
            self._inject_load_library_dex(decode_dir)

    def _inject_load_library_smali(self, decode_dir: Path) -> None:
        """Inject System.loadLibrary call into smali code."""
        from .android_sdk import AndroidSDKService

        # Find main activity
        main_activity = self._find_main_activity(decode_dir)
        if not main_activity:
            raise FridaPatchError("Could not find main activity for injection")

        # Convert activity name to smali path
        smali_path = self._find_smali_class(decode_dir, main_activity)
        if not smali_path:
            raise FridaPatchError(f"Could not find smali file for {main_activity}")

        if self.verbose:
            print(f"Injecting into {smali_path}")

        # Read smali file
        lines = smali_path.read_text().splitlines()

        # Find or create static constructor
        injected = False
        new_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            new_lines.append(line)

            # Look for existing static constructor
            if line.strip().startswith(".method static constructor"):
                # Found static constructor, inject after .locals
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(".locals"):
                    new_lines.append(lines[i])
                    i += 1

                if i < len(lines):  # Found .locals
                    locals_line = lines[i]
                    new_lines.append(locals_line)

                    # Extract locals count and increment
                    match = re.search(r"\.locals (\d+)", locals_line)
                    if match:
                        locals_count = int(match.group(1)) + 1
                        new_lines[-1] = f"    .locals {locals_count}"

                    # Inject loadLibrary call
                    new_lines.extend([
                        "",
                        '    const-string v0, "frida-gadget"',
                        "    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V",
                        ""
                    ])
                    injected = True
            i += 1

        if not injected:
            # No static constructor found, create one
            # Insert before the first method or at the end of the class
            insert_index = -1
            for i, line in enumerate(new_lines):
                if line.strip().startswith(".method") and not line.strip().startswith(".method static constructor"):
                    insert_index = i
                    break

            if insert_index == -1:
                # Insert before .end class
                for i in range(len(new_lines) - 1, -1, -1):
                    if new_lines[i].strip() == ".end class":
                        insert_index = i
                        break

            if insert_index != -1:
                constructor_lines = [
                    "",
                    ".method static constructor <clinit>()V",
                    "    .locals 1",
                    "",
                    '    const-string v0, "frida-gadget"',
                    "    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V",
                    "",
                    "    return-void",
                    ".end method",
                    ""
                ]

                new_lines[insert_index:insert_index] = constructor_lines

        # Write back to file
        smali_path.write_text("\n".join(new_lines))

    def _inject_load_library_dex(self, decode_dir: Path) -> None:
        """Inject using dexpatch for direct DEX manipulation."""
        # This would use dexpatch.jar - simplified implementation
        if self.verbose:
            print("DEX patching not fully implemented - falling back to smali injection")

        self._inject_load_library_smali(decode_dir)

    def _find_main_activity(self, decode_dir: Path) -> Optional[str]:
        """Find the main activity class name."""
        from .android_sdk import AndroidSDKService

        sdk_service = AndroidSDKService(verbose=self.verbose)
        aapt = sdk_service.get_tool_path("aapt")

        # Find original APK to analyze
        apktool_yml = decode_dir / "apktool.yml"
        if not apktool_yml.exists():
            return None

        # For now, parse AndroidManifest.xml directly
        manifest_path = decode_dir / "AndroidManifest.xml"
        if not manifest_path.exists():
            return None

        try:
            # Simple XML parsing to find main activity
            manifest_content = manifest_path.read_text()

            # Look for activity with MAIN action and LAUNCHER category
            import re
            pattern = r'<activity[^>]*android:name="([^"]*)"[^>]*>.*?<action android:name="android\.intent\.action\.MAIN".*?<category android:name="android\.intent\.category\.LAUNCHER"'
            match = re.search(pattern, manifest_content, re.DOTALL)

            if match:
                activity_name = match.group(1)
                if activity_name.startswith("."):
                    # Get package name
                    pkg_match = re.search(r'package="([^"]*)"', manifest_content)
                    if pkg_match:
                        package_name = pkg_match.group(1)
                        activity_name = package_name + activity_name
                return activity_name
        except Exception:
            pass

        return None

    def _find_smali_class(self, decode_dir: Path, class_name: str) -> Optional[Path]:
        """Find smali file for given class name."""
        # Convert class name to path
        class_path = class_name.replace(".", "/") + ".smali"

        # Check in main smali directory
        smali_file = decode_dir / "smali" / class_path
        if smali_file.exists():
            return smali_file

        # Check in smali_classes directories (multidex)
        for smali_dir in decode_dir.glob("smali_classes*"):
            smali_file = smali_dir / class_path
            if smali_file.exists():
                return smali_file

        return None

    def _update_manifest(self, decode_dir: Path, add_network_config: bool) -> None:
        """Update AndroidManifest.xml with required permissions."""
        from ..utils.manifest import ManifestUtils

        manifest_path = decode_dir / "AndroidManifest.xml"
        if not manifest_path.exists():
            return

        # Add INTERNET permission
        ManifestUtils.add_internet_permission(manifest_path)

        # Set extractNativeLibs to true
        ManifestUtils.set_extract_native_libs(manifest_path, True)

        # Add network security config if requested
        if add_network_config:
            ManifestUtils.add_network_security_config(manifest_path)
