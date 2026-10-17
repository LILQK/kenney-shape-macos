#!/usr/bin/env python3
"""Test a disposable copy of a locally built app; keep the selected app intact."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def verify_exports(directory: Path) -> None:
    data = (directory / "potion.stl").read_bytes()
    triangles = struct.unpack("<I", data[80:84])[0]
    if triangles == 0 or len(data) != 84 + triangles * 50:
        raise ValueError("Invalid STL triangle count or length.")
    lines = (directory / "potion.obj").read_text().splitlines()
    vertices = sum(line.startswith("v ") for line in lines)
    faces = sum(line.startswith("f ") for line in lines)
    if vertices == 0 or faces == 0:
        raise ValueError("The OBJ does not contain mesh geometry.")
    document = ET.fromstring((directory / "potion.svg").read_text())
    if not document.findall(".//{http://www.w3.org/2000/svg}path"):
        raise ValueError("The SVG has no shape paths.")
    project = json.loads(gzip.decompress((directory / "roundtrip.kenshape").read_bytes()))
    if project.get("version") != "2.0.0" or len(project["tiles"]) != project["size"]["x"] * project["size"]["y"]:
        raise ValueError("Invalid saved project.")
    print(f"PASS: exported OBJ has {vertices} vertices/{faces} faces; STL has {triangles} triangles; SVG and saved project are valid.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory for the disposable app and results")
    parser.add_argument("--dotnet", default="dotnet")
    args = parser.parse_args()
    try:
        output = args.output.expanduser().absolute()
        output.mkdir(parents=True, exist_ok=False)
        source = args.app.expanduser().resolve()
        copy = output / "Test.app"
        shutil.copytree(source, copy, symlinks=True)
        managed = copy / "Contents/Resources/Data/Managed"
        runner = output / "runner"
        subprocess.run([args.dotnet, "build", str(ROOT / "tests/SmokeRunner/SmokeRunner.csproj"),
                        "-c", "Release", "-o", str(runner), f"-p:GameManagedDirectory={managed}"], check=True)
        shutil.copy2(runner / "MacPortSmokeRunner.dll", managed)
        data = copy / "Contents/Resources/Data"
        assemblies_file = data / "ScriptingAssemblies.json"
        assemblies = json.loads(assemblies_file.read_text())
        assemblies["names"].append("MacPortSmokeRunner.dll")
        assemblies["types"].append(16)
        assemblies_file.write_text(json.dumps(assemblies))
        initialize_file = data / "RuntimeInitializeOnLoads.json"
        initialize = json.loads(initialize_file.read_text())
        initialize["root"].append({
            "assemblyName": "MacPortSmokeRunner", "nameSpace": "MacPortTools.Tests",
            "className": "SmokeRunner", "methodName": "Initialize", "loadTypes": 0,
            "isUnityClass": False,
        })
        initialize_file.write_text(json.dumps(initialize))
        metadata_file = copy / "Contents/Info.plist"
        metadata = plistlib.loads(metadata_file.read_bytes())
        metadata["CFBundleIdentifier"] = "local.macport.kenneyshape.tests"
        metadata_file.write_bytes(plistlib.dumps(metadata))
        (data / "app.info").write_text("Mac Port Tools\nCompatibility Tests")
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(copy)], check=True)
        results = output / "results"
        subprocess.run([str(copy / "Contents/MacOS/KenneyShape"), "-batchmode", "-nographics",
                        "-logFile", str(output / "player.log"), "--mac-port-test-output", str(results)],
                       check=True, timeout=90)
        report = (results / "result.txt").read_text()
        if not report.startswith("PASS: 159 samples;"):
            raise ValueError(report)
        print(report.rstrip())
        verify_exports(results)
        print("The original built app was not modified.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Smoke test failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
