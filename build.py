#!/usr/bin/env python3
"""Build a local macOS app from a user-supplied Kenney Shape Linux release."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
UNITY_VERSION = "2021.3.45f2"
UNITY_REVISION = "88f88f591b2e"
PACKAGE_URL = (
    "https://download.unity3d.com/download_unity/88f88f591b2e/"
    "MacEditorTargetInstaller/UnitySetup-Mac-Mono-Support-for-Editor-2021.3.45f2.pkg"
)
PACKAGE_HASH = "316b0f62177e9025e6cecd33c8de6ef10956f4904397c8117d5dbd3203aba825"
PACKAGE_SIZE = 508688392
ASSEMBLY_HASHES = {
    "Assembly-CSharp.dll": "64b5e7526638656c1766070690be30abcfebc18b02a20356bba2f103f7718a94",
    "Assembly-CSharp-firstpass.dll": "4611852c92d2683f15d7ea2618f855df0b46a2c006e8b86a4d36567dc09c0574",
}
PLAYER_TEMPLATE = "Variations/macos_x64_player_nondevelopment_mono/UnityPlayer.app"


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run(command: list[str], **kwargs) -> None:
    subprocess.run(command, check=True, **kwargs)


def extract_linux_archive(archive: Path, destination: Path) -> None:
    """Extract regular files only; reject links, traversal, and oversized inputs."""
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        if len(entries) > 5000 or sum(item.file_size for item in entries) > 512 * 1024 * 1024:
            raise ValueError("Unexpected Linux archive size or member count.")
        seen: set[str] = set()
        for entry in entries:
            name = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (name.is_absolute() or ".." in name.parts or "\\" in entry.filename
                    or stat.S_ISLNK(mode) or entry.flag_bits & 1):
                raise ValueError(f"Unsupported archive entry: {entry.filename}")
            key = str(name).casefold()
            if key in seen:
                raise ValueError(f"Duplicate archive entry: {entry.filename}")
            seen.add(key)
        source.extractall(destination)


def original_root(directory: Path) -> Path:
    if (directory / "Kenney Shape_Data").is_dir():
        return directory
    candidates = [p.parent for p in directory.glob("*/Kenney Shape_Data") if p.is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError("Expected Kenney Shape_Data, Samples, and Palettes in the Linux release.")


def validate_original(original: Path) -> None:
    for folder in ("Kenney Shape_Data", "Samples", "Palettes"):
        if not (original / folder).is_dir():
            raise ValueError(f"Missing Linux release folder: {folder}")
    # Directory inputs must also be ordinary files, so copying cannot follow an
    # unexpected link outside the selected distribution.
    for folder in ("Kenney Shape_Data", "Samples", "Palettes"):
        directory = original / folder
        if directory.is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
            raise ValueError("The Linux release must not contain symbolic links.")
    data = original / "Kenney Shape_Data"
    for name, expected in ASSEMBLY_HASHES.items():
        path = data / "Managed" / name
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Unsupported or modified {name}; use the original Linux 2.0.0 release.")
    with (data / "globalgamemanagers").open("rb") as source:
        if UNITY_VERSION.encode() + b"\0" not in source.read(128):
            raise ValueError("This release does not use the supported Unity version.")


def validate_module(module: Path) -> None:
    expected = json.loads((ROOT / "tools/runtime-manifest.json").read_text())
    for relative, checksum in expected.items():
        path = module / relative
        if path.is_symlink() or not path.is_file() or digest(path) != checksum:
            raise ValueError(f"Unity module validation failed: {relative}")


def obtain_module(args: argparse.Namespace, cache: Path) -> Path:
    if args.unity_module:
        module = args.unity_module.resolve()
        validate_module(module)
        return module
    module = cache / f"unity-mono-{UNITY_VERSION}"
    if module.exists():
        validate_module(module)
        return module
    package = args.unity_package.resolve() if args.unity_package else cache / f"unity-mono-{UNITY_VERSION}.pkg"
    if not package.exists():
        if not args.download_runtime:
            raise ValueError("Provide --unity-module or --unity-package, or add --download-runtime.")
        print("Downloading the official Unity Mac Mono module (485 MiB).", flush=True)
        temporary = cache / "runtime-download.part"
        try:
            with urllib.request.urlopen(PACKAGE_URL, timeout=45) as response, temporary.open("wb") as target:
                total = 0
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > PACKAGE_SIZE:
                        raise ValueError("The runtime download exceeds its expected size.")
                    target.write(block)
            if temporary.stat().st_size != PACKAGE_SIZE or digest(temporary) != PACKAGE_HASH:
                raise ValueError("The runtime download failed its pinned SHA-256 check.")
            package.parent.mkdir(parents=True, exist_ok=True)
            temporary.rename(package)
        finally:
            temporary.unlink(missing_ok=True)
    if package.stat().st_size != PACKAGE_SIZE or digest(package) != PACKAGE_HASH:
        raise ValueError("Unity package identity mismatch; expected Mac Mono Support 2021.3.45f2.")
    print("Unpacking the verified component locally; installer scripts are not executed.", flush=True)
    with tempfile.TemporaryDirectory(prefix="unity-unpack-", dir=cache) as temporary:
        directory = Path(temporary)
        xar = directory / "package"
        xar.mkdir()
        run(["xar", "-xf", str(package)], cwd=xar)
        payloads = list(xar.glob("*/Payload"))
        if len(payloads) != 1:
            raise ValueError("Unexpected Unity component payload layout.")
        extracted = directory / "module"
        extracted.mkdir()
        with gzip.open(payloads[0], "rb") as source, tempfile.TemporaryFile() as payload:
            shutil.copyfileobj(source, payload)
            payload.seek(0)
            run(["cpio", "-id", "--quiet"], stdin=payload, cwd=extracted)
        validate_module(extracted)
        extracted.rename(module)
    return module


def create_icon(source: Path, destination: Path, scratch: Path) -> None:
    iconset = scratch / "AppIcon.iconset"
    iconset.mkdir()
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            suffix = "@2x" if scale == 2 else ""
            run(["sips", "-z", str(size * scale), str(size * scale), str(source),
                 "--out", str(iconset / f"icon_{size}x{size}{suffix}.png")], stdout=subprocess.DEVNULL)
    run(["iconutil", "-c", "icns", str(iconset), "-o", str(destination)])


def build_app(original: Path, module: Path, app: Path, scratch: Path, dotnet: str) -> None:
    print("Building the Cocoa file dialog adapter.", flush=True)
    run(["sh", str(ROOT / "native/filebrowser/build.sh")])
    shutil.copytree(module / PLAYER_TEMPLATE, app)
    resources = app / "Contents/Resources"
    shutil.copytree(module / "Source/Player/MacPlayer/MacPlayerEntryPoint/Resources",
                    resources, dirs_exist_ok=True)
    shutil.copytree(original / "Kenney Shape_Data", resources / "Data",
                    ignore=shutil.ignore_patterns("MonoBleedingEdge"), dirs_exist_ok=True)
    shutil.copytree(module / "MonoBleedingEdge", app / "Contents/MonoBleedingEdge")
    for name in ("Samples", "Palettes"):
        shutil.copytree(original / name, resources / name)
    if (original / "Readme.txt").is_file():
        shutil.copy2(original / "Readme.txt", resources / "Original-Readme.txt")
    (resources / "Data/Plugins/libFileBrowser.so").unlink(missing_ok=True)
    plugins = app / "Contents/Plugins"
    plugins.mkdir(exist_ok=True)
    shutil.copy2(ROOT / "native/filebrowser/libFileBrowser.dylib", plugins)

    print("Applying compatibility changes to a new copy of the user's assembly.", flush=True)
    patched = scratch / "Assembly-CSharp.dll"
    run([dotnet, "run", "--project", str(ROOT / "tools/AssemblyPatcher"),
         "--configuration", "Release", "--", str(original / "Kenney Shape_Data/Managed/Assembly-CSharp.dll"),
         str(patched)])
    shutil.copy2(patched, resources / "Data/Managed/Assembly-CSharp.dll")
    create_icon(resources / "Data/Resources/UnityPlayer.png", resources / "PlayerIcon.icns", scratch)
    metadata = {
        "CFBundleDevelopmentRegion": "English", "CFBundleExecutable": "KenneyShape",
        "CFBundleIconFile": "PlayerIcon.icns", "CFBundleIdentifier": "local.macport.kenneyshape",
        "CFBundleInfoDictionaryVersion": "6.0", "CFBundleName": "Kenney Shape",
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "2.0.0",
        "CFBundleVersion": "2.0.0", "CFBundleSupportedPlatforms": ["MacOSX"],
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        "LSMinimumSystemVersion": "10.13", "NSHighResolutionCapable": True,
        "NSMainNibFile": "MainMenu", "NSPrincipalClass": "PlayerApplication",
        "UnityBuildNumber": UNITY_REVISION,
        "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True},
    }
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(metadata))
    (app / "Contents/PkgInfo").write_bytes(b"APPL????")
    run(["xcrun", "clang", "-arch", "arm64", "-arch", "x86_64", "-mmacosx-version-min=10.13",
         "-framework", "Cocoa", str(ROOT / "native/launcher.m"), "-o",
         str(app / "Contents/MacOS/KenneyShape")])
    print("Signing and verifying the local application.", flush=True)
    run(["codesign", "--force", "--deep", "--sign", "-", str(app)])
    run(["codesign", "--verify", "--deep", "--strict", str(app)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    original = parser.add_mutually_exclusive_group(required=True)
    original.add_argument("--linux-zip", type=Path, help="Your original Linux 2.0.0 ZIP")
    original.add_argument("--linux-dir", type=Path, help="An extracted original Linux 2.0.0 folder")
    runtime = parser.add_mutually_exclusive_group()
    runtime.add_argument("--unity-module", type=Path, help="An already unpacked official Mac Mono module")
    runtime.add_argument("--unity-package", type=Path, help="The official Mac Mono component PKG")
    parser.add_argument("--download-runtime", action="store_true", help="Download the pinned official Unity component if needed")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / ".cache")
    parser.add_argument("--dotnet", default="dotnet", help="Path or command for the .NET SDK")
    parser.add_argument("--output", type=Path, default=ROOT / "build/Kenney Shape.app", help="New output .app; existing paths are refused")
    args = parser.parse_args()
    try:
        if sys.platform != "darwin":
            raise ValueError("The local builder requires macOS.")
        output = args.output.expanduser().absolute()
        if output.suffix != ".app" or os.path.lexists(output):
            raise ValueError("Choose a new output path ending in .app; existing paths are not overwritten.")
        for command in ("xcrun", "sips", "iconutil", "codesign", "xar", "cpio", args.dotnet):
            if shutil.which(command) is None:
                raise ValueError(f"Required build tool is missing: {command}")
        cache = args.cache_dir.expanduser().resolve()
        cache.mkdir(parents=True, exist_ok=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mac-port-", dir=output.parent) as temporary:
            scratch = Path(temporary)
            if args.linux_zip:
                extracted = scratch / "linux"
                extract_linux_archive(args.linux_zip.expanduser().resolve(), extracted)
                source = original_root(extracted)
            else:
                source = original_root(args.linux_dir.expanduser().resolve())
            validate_original(source)
            if output.is_relative_to(source):
                raise ValueError("Choose an output outside the original Linux distribution.")
            module = obtain_module(args, cache)
            app = scratch / output.name
            build_app(source, module, app, scratch, args.dotnet)
            if os.path.lexists(output):
                raise ValueError("The output appeared during the build; it will not be overwritten.")
            app.rename(output)
        print(f"Built: {output}")
        print("The Unity player is Intel x86_64. Apple silicon requires Rosetta 2.")
        print("This command does not install Rosetta, the Unity Editor, or system components.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
