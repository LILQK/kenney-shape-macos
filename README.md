# Kenney Shape macOS build tools

Unofficial tools for building a local macOS version of **Kenney Shape 2.0.0** from your own Linux download.

This repository contains adapter source, a small assembly patcher, build scripts, and tests. Download Kenney Shape separately from [Kenney's official page](https://kenney.itch.io/kenney-shape). The original application, decompiled source, assets, sample projects, Unity runtime, and compiled adapters are excluded from the repository.

## Requirements

- macOS with the [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/) available (`xcode-select --install`).
- Python 3.9 or later (`python3`).
- [.NET SDK 8 or later](https://dotnet.microsoft.com/download). The patcher rolls forward to newer installed runtimes.
- The unmodified **Kenney Shape 2.0.0 Linux ZIP**. Other builds are rejected by SHA-256 checks.
- About 3 GB of working space while unpacking the Unity component. A fresh download is approximately 485 MiB.
- **Rosetta 2 on Apple silicon.** Follow [Apple's installation instructions](https://support.apple.com/en-us/102527) if needed. The builder never installs it automatically.

The Unity player is **Intel x86_64** and uses OpenGL 4.1. The launcher and Cocoa adapter are universal binaries. This is not a native ARM/Metal port.

## Build

Download the Linux ZIP yourself, then run from the repository directory:

```sh
python3 build.py \
  --linux-zip "$HOME/Downloads/Kenney Shape (Linux).zip" \
  --download-runtime \
  --output "$PWD/build/Kenney Shape.app"
```

The builder validates the selected application, downloads the matching official Unity Mac Mono component, verifies its pinned SHA-256, and unpacks it locally. Package installer scripts are never executed. It then compiles the adapters, patches a copy of the main assembly, creates the app icon from your local distribution, and signs and verifies the resulting app with an ad hoc signature.

The original ZIP and extracted application remain intact. Existing output paths are refused. To build again, choose a new `--output` path or remove your previous generated build yourself.

Open `build/Kenney Shape.app`, or copy that app to Applications. The locally built app is not notarized.

## Existing or offline runtime

Instead of `--download-runtime`, provide the official component package:

```sh
python3 build.py \
  --linux-dir /path/to/extracted-linux-release \
  --unity-package /path/to/UnitySetup-Mac-Mono-Support-for-Editor-2021.3.45f2.pkg \
  --output "$PWD/build/Kenney Shape.app"
```

An already unpacked module can be selected with `--unity-module /path/to/module`. It must contain `Variations`, `MonoBleedingEdge`, and `Source`, and pass the included file-hash manifest. See [the porting notes](docs/PORTING.md) for the exact official download URL and build details. The normal command also reuses a previously verified `.cache` module.

Use `--dotnet /path/to/dotnet` to select an SDK outside your shell's `PATH`.

## Compatibility changes

- The official macOS Intel Unity player replaces the Linux player.
- A Cocoa adapter provides native open/save dialogs through the original file-browser ABI.
- A local bytecode patch sets the resource directory after Unity changes the working directory, so the bundled sample browser works.
- Command is accepted alongside Control by the application's shared shortcut modifier.
- The launcher selects OpenGL 4.1 to use the shaders already present in the Linux release.

No full C# source conversion or Unity Editor installation is required for a normal build.

## Test

The integration test works on a separate copy of your built app and writes its results to a new directory:

```sh
python3 scripts/smoke_test.py \
  --app "$PWD/build/Kenney Shape.app" \
  --output "$PWD/build/smoke-test"
```

It checks the resource-directory fix, native adapter initialization, all 159 bundled samples, tile editing, project save/reload, mesh generation, and OBJ/STL/SVG export. Its headless player log contains expected graphics warnings because the test uses `-nographics`.

The optional native adapter test opens and automatically cancels six Cocoa dialogs:

```sh
sh native/filebrowser/build.sh
sh native/filebrowser/test.sh
```

See [validation and limits](docs/VALIDATION.md) and [troubleshooting](docs/TROUBLESHOOTING.md).

## Publishing this repository

Publish the tools source only. Keep local downloads, `.cache`, `build`, application bundles, DLLs, native binaries, and generated test output outside version control. The supplied `.gitignore` covers these paths, and the release packager uses an explicit source-file allowlist:

```sh
python3 scripts/package.py --output ../kenney-shape-macos-tools.zip
```

The tools license applies only to the original adapter and build-tool code in this repository. It does not grant permission to redistribute Kenney Shape, its modified application bundle, or Unity components. See [third-party materials](THIRD_PARTY.md). Request the relevant rights holders' permission before publishing a built application.

## License

The original build tools and adapter code are available under the [MIT License](LICENSE). Kenney Shape, Unity, and third-party dependencies retain their own licenses. This is an unofficial compatibility project.
