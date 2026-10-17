#!/usr/bin/env python3
"""Package the explicit public source allowlist, excluding local build inputs."""
from __future__ import annotations

import argparse
from pathlib import Path
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = (
    ".gitignore", "LICENSE", "README.md", "THIRD_PARTY.md", "build.py",
    "docs/PORTING.md", "docs/TROUBLESHOOTING.md", "docs/VALIDATION.md",
    "native/launcher.m", "native/filebrowser/FileBrowser.h", "native/filebrowser/FileBrowser.m",
    "native/filebrowser/README.md", "native/filebrowser/build.sh", "native/filebrowser/test.sh",
    "native/filebrowser/probe.m", "native/filebrowser/unit.m",
    "tools/runtime-manifest.json", "tools/AssemblyPatcher/AssemblyPatcher.csproj",
    "tools/AssemblyPatcher/Program.cs", "tools/AssemblyPatcher/packages.lock.json",
    "scripts/package.py", "scripts/smoke_test.py", "tests/test_inputs.py",
    "tests/SmokeRunner/SmokeRunner.csproj", "tests/SmokeRunner/SmokeRunner.cs",
)


def check_source_files() -> None:
    for relative in PUBLIC_FILES:
        source = ROOT / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Missing source file or unsupported symbolic link: {relative}")
        content = source.read_bytes()
        if len(content) > 512 * 1024 or b"\0" in content:
            raise ValueError(f"Unexpected binary or oversized source file: {relative}")
        content.decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New ZIP path; existing files are refused")
    parser.add_argument("--check", action="store_true", help="Validate the source allowlist without creating an archive")
    args = parser.parse_args()
    try:
        check_source_files()
        if args.check:
            print(f"PASS: {len(PUBLIC_FILES)} public text source files; no application or compiled dependency is included.")
            return 0
        if args.output is None:
            parser.error("provide --output or --check")
        output = args.output.expanduser().absolute()
        output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in PUBLIC_FILES:
                source = ROOT / relative
                info = zipfile.ZipInfo(f"kenney-shape-macos/{relative}", (2026, 10, 17, 0, 0, 0))
                mode = 0o755 if source.suffix in (".sh", ".py") else 0o644
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, source.read_bytes())
        print(f"Created source-only archive: {output}")
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
