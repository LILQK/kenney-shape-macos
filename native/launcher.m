#import <Cocoa/Cocoa.h>
#include <mach-o/dyld.h>
#include <libgen.h>
#include <limits.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    @autoreleasepool {
        char executable[PATH_MAX], resolved[PATH_MAX], runtime[PATH_MAX], resources[PATH_MAX];
        uint32_t size = sizeof executable;
        if (_NSGetExecutablePath(executable, &size) != 0 || !realpath(executable, resolved)) return 1;
        char *directory = dirname(resolved);
        snprintf(runtime, sizeof runtime, "%s/UnityPlayer", directory);
        snprintf(resources, sizeof resources, "%s/../Resources", directory);
        if (chdir(resources) != 0) return 1;
        char **arguments = calloc((size_t)argc + 2, sizeof(char *));
        if (!arguments) return 1;
        arguments[0] = runtime;
        arguments[1] = "-force-glcore41";
        for (int i = 1; i < argc; ++i) arguments[i + 1] = argv[i];
        execv(runtime, arguments);
        int failure = errno;
        [NSApplication sharedApplication];
        NSAlert *alert = [[NSAlert alloc] init];
        alert.messageText = @"Kenney Shape could not start";
        alert.informativeText = failure == EBADARCH || failure == ENOEXEC
            ? @"This build uses the Intel Unity player and needs Rosetta 2 on Apple silicon. Install Rosetta 2, then open Kenney Shape again."
            : [NSString stringWithFormat:@"The Unity player could not be launched: %s", strerror(failure)];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];
        free(arguments);
        return failure;
    }
}
