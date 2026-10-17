# Troubleshooting

## Missing build tools

Install Apple's Xcode Command Line Tools and the .NET SDK from their official sources. Confirm that `xcrun --find clang`, `python3 --version`, and `dotnet --info` work in the terminal used to run the builder. A custom SDK path can be selected with `--dotnet`.

Python 3.9 or later is required. The Python builder uses the standard library only. The patcher restores its pinned Mono.Cecil dependency from NuGet.

## Unsupported assembly

Use a fresh copy of the official Kenney Shape 2.0.0 Linux distribution. A previously patched assembly, another platform, an older release, or changed files will fail the version checks. The builder deliberately refuses unknown inputs.

## Missing Unity module

Add `--download-runtime`, supply the exact official `.pkg` with `--unity-package`, or select an unpacked module with `--unity-module`. A verified cached module is reused automatically. The normal builder unpacks the `.pkg` itself; do not run its installer to prepare a build.

If a download or module hash does not match, obtain the component again from the official Unity link. Inspect a cache before removing it, then remove only the builder's `.cache` directory if you want a fresh download. Do not change the expected hashes to bypass a mismatch.

## Existing output

The output path must not exist. Choose another `--output` path, or remove your previous generated build after saving any files you placed inside it. The original download should be kept separately.

## Apple silicon cannot start the player

The app uses the Intel Unity runtime. Install Rosetta 2 using [Apple's documented process](https://support.apple.com/en-us/102527). A universal launcher does not make the Unity runtime native ARM.

## macOS security prompt

The app has a local ad hoc signature and no Developer ID notarization. Verify the build inputs and inspect the macOS message before deciding whether to open a locally built app. This project does not disable Gatekeeper or remove quarantine attributes automatically.

## Blank graphics or shader errors

Use the generated launcher so `-force-glcore41` is supplied. Do not force Metal: its shader programs are not present in the supported Linux build. The headless integration test intentionally uses `-nographics` and therefore logs shader warnings; these do not describe the interactive renderer.

The normal Unity log is usually under `~/Library/Logs/Kenney/Kenney Shape/Player.log`. To choose a separate log for diagnosis:

```sh
'build/Kenney Shape.app/Contents/MacOS/KenneyShape' \
  -logFile "$PWD/build/player.log"
```

Review logs and remove personal paths or other private information before sharing them.

## Samples do not open

Build from the original Linux distribution using the current script. It applies the resource-directory fix to a copy of the main assembly. Moving only the runtime into an app bundle without that compatibility change does not preserve the relative sample paths.

## Reporting a problem

Include the macOS version, processor architecture, supported application version, build command with private paths removed, and the exact failure message. Do not attach the original application, game assemblies, assets, or built app bundle to a public issue.
