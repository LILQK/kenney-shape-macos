# Validation and limits

Validation was performed on 17 October 2026 using an Apple M4 Mac running macOS 27.0.1, Rosetta 2, the supported Linux 2.0.0 application, and Unity 2021.3.45f2. This is a compatibility test record, not a guarantee for every Mac or export setting.

## Source-only build flow

The builder was run against the original Linux ZIP and the separately obtained official Mac Mono support component. It built the Cocoa adapter, patched the original assembly locally, created the app bundle, and passed strict signature verification. The assembly patcher does not require a decompiled application source tree.

Input checks refuse unrecognized application assemblies and modified runtime files. Synthetic archive tests exercise path traversal, absolute paths, symbolic links, case-colliding members, and preservation of the selected ZIP:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Integration test

The included `scripts/smoke_test.py` creates a disposable app copy and adds a separate test assembly compiled against the user's local application libraries. It does not alter the selected built app or include the test runner in production builds.

The test passed these checks in the actual macOS player:

- The resource-directory helper runs after Unity's startup directory change.
- The original managed file-browser wrapper loads the Cocoa adapter.
- All 159 supplied sample projects load with consistent tile counts.
- A tile can be edited, restored, saved, and reloaded.
- The potion sample generates 64 mesh instances with 1680 source vertices.
- OBJ, binary STL, and SVG exports are written successfully.
- Independent parsing validates an OBJ with 318 vertices and 920 faces, an STL with 920 triangles and a matching byte length, a nonempty SVG, and a valid compressed project saved as version 2.0.0.

The integration player uses `-batchmode -nographics`. Shader warnings in that test are expected. They do not establish interactive rendering quality. A separate interactive launch created an OpenGL 4.1 context on the Apple M4 and displayed the original interface and 3D preview.

## Native adapter tests

The Cocoa adapter passed 14 direct parsing/result checks and 59 assertions across six self-cancelling real dialogs. The checks cover file/folder/save modes, multiple selection, named extension groups, wildcard handling, UTF-8 titles/default filenames, cancellation, and asynchronous callbacks. Architecture slices, exported ABI symbols, and local signing were also verified.

## Remaining coverage

- Successful manual file selection through the complete application UI is not automated by these tests.
- Command modifier handling is patched in bytecode; every shortcut combination has not been exercised interactively.
- GIF, FBX, DAE, glTF, VOX, Minecraft output, image import, and every export option are outside the integration suite.
- The Intel deployment target is macOS 10.13, but older macOS releases and physical Intel hardware were not tested.
- Native ARM/Metal rendering is unsupported by this builder.

Local logs and exported test files stay in the chosen test directory. They are excluded from the public source package.
