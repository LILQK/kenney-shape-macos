# Testing notes

The current build was tested on an Apple M4 with macOS 27.0.1 and Rosetta 2, using Kenney Shape 2.0.0 for Linux. Both the unpacked Unity module and the official component package worked as build inputs. The resulting apps passed `codesign --verify --deep --strict`.

## App tests

`scripts/smoke_test.py` makes a separate copy of a built app and adds a test runner to that copy. Run it with a new output directory each time:

```sh
python3 scripts/smoke_test.py \
  --app "$PWD/build/Kenney Shape.app" \
  --output "$PWD/build/smoke-test"
```

The test loaded all 159 sample projects, checked the resource folder and file-dialog adapter, edited a tile, and saved and reloaded a project. It also generated a model from the potion sample and exported OBJ, STL, and SVG files. The script checks the exported geometry, SVG paths, and compressed project file.

The test runs with `-batchmode -nographics`, so shader warnings in its log are expected. A separate interactive run displayed the original interface and 3D preview through an OpenGL 4.1 context.

## File dialogs

To test the Cocoa adapter on its own:

```sh
sh native/filebrowser/build.sh
sh native/filebrowser/test.sh
```

This opens six dialogs and cancels them automatically. It checks file, folder, and save modes; extension filters; UTF-8 text; multiple-selection settings; cancellation; and async callbacks. There are also tests for parsing filters and formatting returned paths.

## Build inputs

These tests use small synthetic ZIPs and don't need an application download:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

They check extraction, preservation of the input ZIP, and rejection of paths or links that could escape the extraction folder. The assembly patcher was also checked against unknown inputs, an already patched assembly, and attempts to overwrite existing files.

## Still to test

- Older macOS releases and physical Intel Macs.
- Successful file selection through the full app UI; the automated dialog tests cover cancellation.
- The full set of Command-key shortcuts.
- Image import, GIF, FBX, DAE, glTF, VOX, Minecraft output, and the remaining export options.

Logs and exported files are saved in the test output directory.
