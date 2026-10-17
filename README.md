# Kenney Shape on macOS

Build a macOS app from the Linux version of [Kenney Shape](https://kenney.itch.io/kenney-shape).

This uses the Intel Unity player with OpenGL 4.1, so Apple silicon Macs need Rosetta 2. It works with the original **2.0.0 Linux release**.

## What you need

- The Kenney Shape 2.0.0 Linux ZIP from the official download page.
- [Xcode Command Line Tools](https://developer.apple.com/xcode/resources/) (`xcode-select --install`).
- Python 3.9 or newer and the [.NET SDK 8 or newer](https://dotnet.microsoft.com/download).
- [Rosetta 2](https://support.apple.com/en-us/102527) on Apple silicon.
- About 3 GB of free space for the build.

## Build

From the repository directory, run:

```sh
python3 build.py \
  --linux-zip "$HOME/Downloads/Kenney Shape (Linux).zip" \
  --download-runtime \
  --output "$PWD/build/Kenney Shape.app"
```

Adjust the ZIP path if you saved it somewhere else. When the build finishes, open `build/Kenney Shape.app` or copy it to Applications.

The first build downloads the matching Unity Mac Mono component, about 485 MiB. Later builds reuse the copy in `.cache`. The script unpacks the component without running its installer, so you don't need to install the Unity Editor.

Your Linux download stays untouched. Choose a new output path for each build; the script won't overwrite an existing app.

If you already have the Unity component, use `--unity-package /path/to/component.pkg` or `--unity-module /path/to/unpacked/module` instead of `--download-runtime`. You can also select an extracted Linux folder with `--linux-dir`, or a particular SDK with `--dotnet`. Run `python3 build.py --help` for all options.

## How it works

The builder combines your Linux app's resources with the matching macOS Unity player. A Cocoa adapter supplies the file dialogs, and two small changes to a local copy of the main assembly fix the sample folder path and add Command-key shortcuts. The launcher selects OpenGL 4.1 to use the shaders already included in the Linux build.

The [porting notes](docs/PORTING.md) cover the runtime version, patch, and bundle layout.

## Testing

To check a built app:

```sh
python3 scripts/smoke_test.py \
  --app "$PWD/build/Kenney Shape.app" \
  --output "$PWD/build/smoke-test"
```

This runs a separate copy of the app, loads the samples, and checks editing, saving, reloading, and OBJ/STL/SVG export. See [testing notes](docs/VALIDATION.md) for the native dialog tests and remaining gaps.

## Compatibility

The build has been tested on an Apple M4 running macOS 27.0.1 with Rosetta 2. Older macOS versions and Intel Macs still need testing.

The app uses an Intel runtime and OpenGL; native ARM/Metal rendering would need more work. It has a local ad hoc signature and is not notarized. If you run into a problem, start with [troubleshooting](docs/TROUBLESHOOTING.md).

## License

The build tools and adapters are [MIT licensed](LICENSE). Kenney Shape and Unity are downloaded separately and keep their own licenses; see [third-party materials](THIRD_PARTY.md). This is an unofficial project.
