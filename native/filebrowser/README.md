# Cocoa file dialog adapter

This adapter implements the application's seven existing native file-browser entry points with macOS `NSOpenPanel` and `NSSavePanel`. The C header documents the complete ABI.

The library is built locally as a universal binary: x86_64 targets macOS 10.13 and arm64 targets macOS 11. The app's Unity runtime remains Intel. The builder places the library at `Contents/Plugins/libFileBrowser.dylib`.

The ABI uses UTF-8 strings, four-byte managed BOOL parameters, and C callback pointers. Cancellation returns an empty string. Multiple selections are separated by U+001C. Synchronous strings remain valid until that caller thread opens another synchronous dialog; callback strings remain valid for the duration of the callback.

Extension filters use `Label;ext,ext|Other label;ext`. Named groups appear in the Format menu. Wildcard or empty groups allow all files. The adapter supports default filenames, initial directories, file/folder selection, and synchronous/asynchronous calls. AppKit operations and async callbacks run on the main thread.

Build and optionally test:

```sh
sh build.sh
sh test.sh
```

The test program opens six real Cocoa dialogs and cancels them automatically. It checks panel modes, multiple-selection settings, filters, wildcards, UTF-8 titles/default filenames, cancellation, and callbacks. Separate assertions check filter parsing and result formatting. These tests do not simulate a user's successful selection through the full application's UI.

Compiled libraries and test executables are local build outputs and are excluded from the source release.
