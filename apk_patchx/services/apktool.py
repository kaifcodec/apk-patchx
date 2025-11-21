"""Apktool service for APK operations."""

import subprocess
from pathlib import Path
from typing import List, Optional

from ..exceptions import BuildError, NetworkError, ToolNotFoundError, ValidationError
from ..utils.core import run_command, get_apkpatchx_home, download_file
from ..utils.versions import get_latest_github_release
from .android_sdk import AndroidSDKService


class ApktoolService:
    """Service for apktool operations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.sdk_service = AndroidSDKService(verbose=verbose)
        self._apktool_path: Optional[Path] = None

    @property
    def apktool_path(self) -> Path:
        """Get apktool JAR path."""
        if self._apktool_path is None:
            self._ensure_apktool()
        return self._apktool_path

    def _ensure_apktool(self) -> None:
        """Ensure apktool is available."""
        tools_dir = get_apkpatchx_home() / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        for jar_file in tools_dir.glob("apktool_*.jar"):
            self._apktool_path = jar_file
            return


        if self.verbose:
            print("Downloading latest apktool...")

        try:
            latest_version = get_latest_github_release("iBotPeaches", "Apktool")
            jar_name = f"apktool_{latest_version}.jar"
            jar_url = f"https://github.com/iBotPeaches/Apktool/releases/download/v{latest_version}/{jar_name}"

            jar_path = tools_dir / jar_name
            download_file(jar_url, jar_path)

            self._apktool_path = jar_path

            if self.verbose:
                print(f"Downloaded apktool {latest_version}")

        except Exception as e:
            raise NetworkError(f"Failed to download apktool: {e}")

    def decode(self, apk_path: Path, output_dir: Optional[Path] = None,
              no_resources: bool = False, no_sources: bool = False,
              only_main_classes: bool = False, extra_args: Optional[str] = None) -> Path:
        """Decode APK file."""
        if not apk_path.exists():
            raise ValidationError(f"APK file not found: {apk_path}")

        if output_dir is None:
            output_dir = apk_path.parent / apk_path.stem

        self.sdk_service.ensure_java()

        cmd = ["java", "-jar", str(self.apktool_path), "d", str(apk_path)]

        if no_resources:
            cmd.append("-r")
        if no_sources:
            cmd.append("-s")
        if only_main_classes:
            cmd.append("--only-main-classes")

        cmd.extend(["-o", str(output_dir)])

        if extra_args:
            cmd.extend(extra_args.split())

        if self.verbose:
            print(f"Decoding {apk_path} to {output_dir}...")

        result = run_command(cmd)
        if result.returncode != 0:
            raise BuildError(f"Failed to decode APK: {apk_path}")

        return output_dir

    def build(self, source_dir: Path, output_path: Path,
             add_network_config: bool = False, extra_args: Optional[str] = None) -> Path:
        """Build APK from source directory."""
        if not source_dir.exists():
            raise ValidationError(f"Source directory not found: {source_dir}")

        self.sdk_service.ensure_java()


        if add_network_config:
            self._add_network_security_config(source_dir)

        cmd = ["java", "-jar", str(self.apktool_path), "b", str(source_dir)]
        cmd.extend(["-o", str(output_path)])
        cmd.extend(["--use-aapt2"])

        if extra_args:
            cmd.extend(extra_args.split())

        if self.verbose:
            print(f"Building {source_dir} to {output_path}...")

        result = run_command(cmd)
        if result.returncode != 0:
            raise BuildError(f"Failed to build APK from: {source_dir}")

        return output_path

    def _add_network_security_config(self, source_dir: Path) -> None:
        """Add permissive network security configuration."""
        from ..utils.manifest import ManifestUtils


        xml_dir = source_dir / "res" / "xml"
        xml_dir.mkdir(parents=True, exist_ok=True)

        network_config = xml_dir / "network_security_config.xml"
        network_config.write_text("""<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">localhost</domain>
        <domain includeSubdomains="true">10.0.0.0/8</domain>
        <domain includeSubdomains="true">172.16.0.0/12</domain>
        <domain includeSubdomains="true">192.168.0.0/16</domain>
    </domain-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system"/>
            <certificates src="user"/>
        </trust-anchors>
    </base-config>
</network-security-config>
""")

        manifest_path = source_dir / "AndroidManifest.xml"
        if manifest_path.exists():
            ManifestUtils.add_network_security_config(manifest_path)

