#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p build
for arch in arm64 x86_64; do
    deployment_target=11.0
    if [ "$arch" = x86_64 ]; then deployment_target=10.13; fi
    xcrun clang -fobjc-arc -fvisibility=hidden -Wall -Wextra -Werror \
        -arch "$arch" -mmacosx-version-min="$deployment_target" -dynamiclib FileBrowser.m \
        -framework Cocoa -install_name @rpath/libFileBrowser.dylib \
        -o "build/libFileBrowser.$arch.dylib"
done
xcrun lipo -create build/libFileBrowser.arm64.dylib build/libFileBrowser.x86_64.dylib \
    -output libFileBrowser.dylib
codesign --force --sign - libFileBrowser.dylib
