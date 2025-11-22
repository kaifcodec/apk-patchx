import sys
from pathlib import Path
from typing import Optional

import click
import colorama
from colorama import Fore, Style

from . import __version__
from .exceptions import APKPatchxError
from .services.adb import ADBService
from .services.apktool import ApktoolService
from .services.frida import FridaService
from .services.signing import SigningService
from .utils.core import setup_logging, get_apkpatchx_home

colorama.init(autoreset=True)


def print_error(message: str) -> None:
    """Print error message in red."""
    click.echo(f"{Fore.RED}[!] {message}{Style.RESET_ALL}", err=True)


def print_success(message: str) -> None:
    """Print success message in green.""" 
    click.echo(f"{Fore.GREEN}[+] {message}{Style.RESET_ALL}")


def print_info(message: str) -> None:
    """Print info message in blue."""
    click.echo(f"{Fore.BLUE}[*] {message}{Style.RESET_ALL}")


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    click.echo(f"{Fore.YELLOW}[!] {message}{Style.RESET_ALL}")


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, version: bool) -> None:
    """APKPatchx - Android APK manipulation toolkit."""
    if version:
        click.echo(f"APKPatchx {__version__}")
        sys.exit(0)

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        sys.exit(0)

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose)


    home = get_apkpatchx_home()
    home.mkdir(parents=True, exist_ok=True)

    if verbose:
        print_info(f"APKPatchx home: {home}")


@cli.command()
@click.argument("package_name")
@click.option("--net", is_flag=True, help="Add permissive network security config")
@click.option("--apktool-decode-args", help="Additional apktool decode arguments")
@click.option("--apktool-build-args", help="Additional apktool build arguments")
@click.pass_context
def pull(ctx: click.Context, package_name: str, net: bool, apktool_decode_args: Optional[str], apktool_build_args: Optional[str]) -> None:
    """Pull APK from connected device."""
    try:
        verbose = ctx.obj.get("verbose", False)
        adb_service = ADBService(verbose=verbose)
        apktool_service = ApktoolService(verbose=verbose)
        signing_service = SigningService(verbose=verbose)

        print_info(f"Pulling {package_name} from device...")
        apk_paths = adb_service.pull_package(package_name)

        if len(apk_paths) > 1:
            from .services.split_merge import SplitMergeService
            merge_service = SplitMergeService(verbose=verbose)
            output_path = merge_service.merge_split_apks(apk_paths, net=net)
            print_success(f"Merged split APKs to: {output_path}")
        else:
            print_success(f"Pulled APK to: {apk_paths[0]}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("apk_file", type=click.Path(exists=True, path_type=Path))
@click.option("--no-res", "-r", is_flag=True, help="Do not decode resources")
@click.option("--no-src", "-s", is_flag=True, help="Do not disassemble DEX")
@click.option("--only-main-classes", is_flag=True, help="Only disassemble main DEX classes")
@click.option("--apktool-decode-args", help="Additional apktool decode arguments")
@click.pass_context
def decode(ctx: click.Context, apk_file: Path, no_res: bool, no_src: bool, 
          only_main_classes: bool, apktool_decode_args: Optional[str]) -> None:
    """Decode APK file."""
    try:
        verbose = ctx.obj.get("verbose", False)
        apktool_service = ApktoolService(verbose=verbose)

        print_info(f"Decoding {apk_file}...")
        output_dir = apktool_service.decode(
            apk_file,
            no_resources=no_res,
            no_sources=no_src,
            only_main_classes=only_main_classes,
            extra_args=apktool_decode_args
        )
        print_success(f"Decoded to: {output_dir}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("apk_dir", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", help="Output APK path", type=click.Path(path_type=Path))
@click.option("--net", is_flag=True, help="Add permissive network security config")
@click.option("--apktool-build-args", help="Additional apktool build arguments")
@click.pass_context
def build(ctx: click.Context, apk_dir: Path, output: Optional[Path], 
         net: bool, apktool_build_args: Optional[str]) -> None:
    """Build APK from decoded directory."""
    try:
        verbose = ctx.obj.get("verbose", False)
        apktool_service = ApktoolService(verbose=verbose)
        signing_service = SigningService(verbose=verbose)

        if output is None:
            output = apk_dir.with_suffix(".apk")

        print_info(f"Building {apk_dir}...")
        apk_path = apktool_service.build(
            apk_dir,
            output,
            add_network_config=net,
            extra_args=apktool_build_args
        )

        print_info("Signing APK...")
        signed_path = signing_service.sign_apk(apk_path)
        print_success(f"Built and signed: {signed_path}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("apk_file", type=click.Path(exists=True, path_type=Path))
@click.option("--arch", "-a", required=True, 
              type=click.Choice(["arm", "arm64", "x86", "x86_64"]),
              help="Target architecture")
@click.option("--gadget-conf", "-g", type=click.Path(exists=True, path_type=Path),
              help="Frida gadget configuration file")
@click.option("--net", is_flag=True, help="Add permissive network security config")
@click.option("--no-src", "-s", is_flag=True, help="Do not disassemble DEX")
@click.option("--only-main-classes", is_flag=True, help="Only disassemble main DEX classes")
@click.option("--frida-version", help="Specific Frida version to use")
@click.option("--apktool-decode-args", help="Additional apktool decode arguments")
@click.option("--apktool-build-args", help="Additional apktool build arguments")
@click.pass_context
def patch(ctx: click.Context, apk_file: Path, arch: str, gadget_conf: Optional[Path],
         net: bool, no_src: bool, only_main_classes: bool, frida_version: Optional[str],
         apktool_decode_args: Optional[str], apktool_build_args: Optional[str]) -> None:
    """Patch APK with Frida gadget."""
    try:
        verbose = ctx.obj.get("verbose", False)
        frida_service = FridaService(verbose=verbose)

        print_info(f"Patching {apk_file} with Frida gadget ({arch})...")
        output_path = frida_service.patch_apk(
            apk_file,
            arch,
            gadget_config=gadget_conf,
            add_network_config=net,
            no_sources=no_src,
            only_main_classes=only_main_classes,
            frida_version=frida_version,
            decode_args=apktool_decode_args,
            build_args=apktool_build_args
        )
        print_success(f"Patched APK: {output_path}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("apk_file", type=click.Path(exists=True, path_type=Path))
@click.argument("new_package")
@click.option("--net", is_flag=True, help="Add permissive network security config")
@click.pass_context
def rename(ctx: click.Context, apk_file: Path, new_package: str, net: bool) -> None:
    """Rename APK package."""
    try:
        verbose = ctx.obj.get("verbose", False)
        apktool_service = ApktoolService(verbose=verbose)
        signing_service = SigningService(verbose=verbose)

        print_info(f"Renaming {apk_file} to {new_package}...")


        decoded_dir = apktool_service.decode(apk_file, no_resources=False, no_sources=True)

        apktool_yml = decoded_dir / "apktool.yml"
        content = apktool_yml.read_text()

        if "renameManifestPackage:" in content:
            import re
            content = re.sub(r"renameManifestPackage:.*", f"renameManifestPackage: {new_package}", content)
        else:
            content += f"\nrenameManifestPackage: {new_package}\n"

        apktool_yml.write_text(content)


        output_path = apk_file.parent / f"{apk_file.stem}.renamed.apk"
        built_path = apktool_service.build(decoded_dir, output_path, add_network_config=net)
        signed_path = signing_service.sign_apk(built_path)

        print_success(f"Renamed APK: {signed_path}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


@cli.command()
@click.argument("apk_file", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def sign(ctx: click.Context, apk_file: Path) -> None:
    """Sign APK file."""
    try:
        verbose = ctx.obj.get("verbose", False)
        signing_service = SigningService(verbose=verbose)

        print_info(f"Signing {apk_file}...")
        signed_path = signing_service.sign_apk(apk_file)
        print_success(f"Signed APK: {signed_path}")

    except APKPatchxError as e:
        print_error(str(e))
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        print_error("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

