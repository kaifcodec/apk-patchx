"""Android manifest manipulation utilities."""

import re
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from ..exceptions import ValidationError


class ManifestUtils:
    """Utilities for AndroidManifest.xml manipulation."""

    @staticmethod
    def add_internet_permission(manifest_path: Path) -> None:
        """Add INTERNET permission to manifest if not present."""
        content = manifest_path.read_text()

        if "android.permission.INTERNET" in content:
            return

        # find manifest tag and add permissi-on
        lines = content.splitlines()
        manifest_found = False

        for i, line in enumerate(lines):
            if "<manifest" in line:
                manifest_found = True
            elif manifest_found and ("<application" in line or "<uses-" in line):
                # insert before application or other uses- tags
                lines.insert(i, '    <uses-permission android:name="android.permission.INTERNET" />')
                break
        else:

            for i, line in enumerate(lines):
                if "<manifest" in line and ">" in line:
                    lines.insert(i + 1, '    <uses-permission android:name="android.permission.INTERNET" />')
                    break

        manifest_path.write_text("\n".join(lines))

    @staticmethod
    def set_extract_native_libs(manifest_path: Path, extract: bool = True) -> None:
        """Set android:extractNativeLibs attribute."""
        content = manifest_path.read_text()

        extract_value = "true" if extract else "false"


        if "android:extractNativeLibs" in content:
            content = re.sub(
                r'android:extractNativeLibs="[^"]*"',
                f'android:extractNativeLibs="{extract_value}"',
                content
            )
        else:

            content = re.sub(
                r'(<application[^>]*)',
                rf'\1 android:extractNativeLibs="{extract_value}"',
                content
            )

        manifest_path.write_text(content)

    @staticmethod
    def add_network_security_config(manifest_path: Path) -> None:
        """Add network security config to application."""
        content = manifest_path.read_text()

        if "android:networkSecurityConfig" in content:
            return

        # Add to application tag
        content = re.sub(
            r'(<application[^>]*)',
            r'\1 android:networkSecurityConfig="@xml/network_security_config"',
            content
        )

        manifest_path.write_text(content)

    @staticmethod
    def disable_apk_splitting(manifest_path: Path) -> None:
        """Disable APK splitting in manifest."""
        content = manifest_path.read_text()


        content = re.sub(
            r'android:isSplitRequired="true"',
            'android:isSplitRequired="false"',
            content
        )

        content = re.sub(
            r'(<meta-data[^>]*android:name="com\.android\.vending\.splits\.required"[^>]*android:value=")[^"]*(")',
            r'\1false\2',
            content
        )

        manifest_path.write_text(content)

    @staticmethod
    def get_package_name(manifest_path: Path) -> Optional[str]:
        """Extract package name from manifest."""
        try:
            content = manifest_path.read_text()
            match = re.search(r'package="([^"]*)"', content)
            return match.group(1) if match else None
        except Exception:
            return None

    @staticmethod
    def get_main_activity(manifest_path: Path) -> Optional[str]:
        """Extract main activity name from manifest."""
        try:
            content = manifest_path.read_text()

            # look for activity with MAIN action and LAUNCHER category
            pattern = (
                r'<activity[^>]*android:name="([^"]*)"[^>]*>.*?'
                r'<action android:name="android\.intent\.action\.MAIN".*?'
                r'<category android:name="android\.intent\.category\.LAUNCHER"'
            )
            match = re.search(pattern, content, re.DOTALL)

            if match:
                activity_name = match.group(1)
                if activity_name.startswith("."):

                    package = ManifestUtils.get_package_name(manifest_path)
                    if package:
                        activity_name = package + activity_name
                return activity_name

        except Exception:
            pass

        return None
