# Porting notes

## Supported input

The supported distribution is Kenney Shape 2.0.0 for Linux, built with Unity **2021.3.45f2**, revision **88f88f591b2e**. Both application assemblies are checked against pinned SHA-256 values before copying or patching them. The serialized manager header is checked for the matching engine version.

The folder layout is:

```text
Linux release/
  Kenney Shape.x86_64
  UnityPlayer.so
  Kenney Shape_Data/
  Samples/
  Palettes/
```

ZIP extraction rejects encrypted members, symbolic links, path traversal, duplicate paths, and unexpectedly large archives. Directory inputs are checked for symbolic links. The builder never edits files in this distribution.

## Runtime selection

The Linux resources contain OpenGL Core and Vulkan shader programs. They do not include Metal shader programs. A native ARM player test selected a null graphics device when forced to OpenGL; forcing Metal failed because that backend was absent from the application build.

The macOS Intel player can use the existing OpenGL Core programs. On the tested Apple silicon machine it runs through Rosetta 2 and creates a real OpenGL 4.1 context. This preserves the original serialized resources and drawing/model tools.

The official component is:

[Unity Mac Mono Support for Editor 2021.3.45f2](https://download.unity3d.com/download_unity/88f88f591b2e/MacEditorTargetInstaller/UnitySetup-Mac-Mono-Support-for-Editor-2021.3.45f2.pkg)

```text
Size:    508688392 bytes
SHA-256: 316b0f62177e9025e6cecd33c8de6ef10956f4904397c8117d5dbd3203aba825
```

The builder extracts the XAR container, decompresses its gzip/cpio payload, and selects `Variations/macos_x64_player_nondevelopment_mono/UnityPlayer.app`. It copies the matching Mono configuration and entry-point resources. The file hashes of these inputs are recorded in `tools/runtime-manifest.json`; the repository contains the hashes only.

The [Unity release page](https://unity.com/releases/editor/whats-new/2021.3.45f2) documents the matching engine build. The component is downloaded from Unity when explicitly requested or supplied locally. The builder does not install the Unity Editor or invoke the component's installer scripts.

## Native adapters

`native/launcher.m` forwards command-line arguments to the Intel player and adds `-force-glcore41`. It displays an explanation if the runtime cannot start, including the missing-Rosetta case. It does not install dependencies or change security settings.

`native/filebrowser` implements seven C entry points using `NSOpenPanel` and `NSSavePanel`. This matches the application's existing managed file-browser imports. The Linux platform selection is compiled into the supplied managed library, so its ABI remains in use after replacing the player.

The adapter supports synchronous and asynchronous file/folder/save dialogs, UTF-8 paths, extension groups, wildcard filters, default filenames, and multiple selections separated by U+001C. AppKit operations run on the main thread. See the [adapter notes](../native/filebrowser/README.md).

## Local assembly patch

`tools/AssemblyPatcher` uses Mono.Cecil to modify a copy of the user's main assembly. Its source contains compatibility logic and method/field selectors; it does not contain the original application's method implementations.

Two changes are applied:

1. A helper is called at the start of `ProjectManager.Awake`. It selects the app's `Contents/Resources` directory when that directory exists. Unity changes the process directory after the native launcher runs, so changing it only in the launcher is insufficient.
2. After `EventManager.Update` stores its existing control-modifier value, additional instructions combine that value with the left and right Command keys. Existing Control behavior remains available.

Original assembly references are retained, including the Unity-compatible core-library scope. The patcher does not import .NET 8 runtime references into the application assembly. Unknown, already patched, or signed inputs are refused. The output must be a new file.

The output app retains the original auxiliary managed assemblies and serialized resources. The original Linux file-browser `.so` is removed from the output copy and replaced by the locally compiled Cocoa library.

## Bundle and signing

```text
Kenney Shape.app/Contents/
  MacOS/KenneyShape              universal launcher
  MacOS/UnityPlayer              official Intel player
  Frameworks/                   matching player and Mono libraries
  MonoBleedingEdge/etc/          matching Mono configuration
  Plugins/libFileBrowser.dylib   locally compiled Cocoa adapter
  Resources/Data/                local copy of the application's resources
  Resources/Samples/             local copy of the supplied samples
  Resources/Palettes/            local copy of the supplied palettes
```

The original icon is converted to ICNS during the local build. The app is ad hoc signed and checked with `codesign --verify --deep --strict`. It is not notarized. Builds happen in a temporary directory beside the requested output and are moved into place only after verification succeeds.

The Intel binaries declare macOS 10.13 as their minimum target. This is a binary deployment target, not a claim that all older macOS releases have been tested. Native ARM/Metal support would require additional work on the missing shader programs.
