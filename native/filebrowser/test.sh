#!/bin/sh
set -eu
cd "$(dirname "$0")"
xcrun clang -fobjc-arc -Wall -Wextra -Werror unit.m \
    -framework Cocoa -o build/unit
./build/unit
xcrun clang -fobjc-arc -Wall -Wextra -Werror probe.m \
    -framework Cocoa -L. -lFileBrowser -Wl,-rpath,@loader_path/.. -o build/probe
./build/probe
xcrun lipo -archs libFileBrowser.dylib
nm -gU libFileBrowser.dylib
codesign --verify --strict libFileBrowser.dylib
