#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include "FileBrowser.h"

static NSUInteger checks = 0;
static int expectedKind = 0;
static BOOL expectedMultiple = NO;
static BOOL callbackDone = NO;
static NSUInteger observedPanels = 0;

static void check(BOOL condition, const char *message) {
    checks++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

@interface NSOpenPanel (FBProbe)
+ (NSOpenPanel *)fbProbeOpenPanel;
@end
@interface NSSavePanel (FBProbe)
+ (NSSavePanel *)fbProbeSavePanel;
@end

static void checkAndCancel(NSSavePanel *panel) {
    observedPanels++;
    check([panel.message hasPrefix:@"File dialog test"], "UTF-8 panel title transferred");
    check(panel.canCreateDirectories, "new directories enabled");
    if (expectedKind == 1 || expectedKind == 2) {
        check([panel isKindOfClass:[NSOpenPanel class]], "open panel class");
        NSOpenPanel *open = (NSOpenPanel *)panel;
        check(open.allowsMultipleSelection == expectedMultiple, "four-byte BOOL marshalling");
        check(open.canChooseDirectories == (expectedKind == 2), "folder selection mode");
        check(open.canChooseFiles == (expectedKind == 1), "file selection mode");
    }
    if (expectedKind != 2) {
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
        check([panel.allowedFileTypes isEqualToArray:@[@"png", @"jpg"]], "extension group parsing");
        NSPopUpButton *menu = nil;
        for (NSView *view in panel.accessoryView.subviews)
            if ([view isKindOfClass:[NSPopUpButton class]]) menu = (NSPopUpButton *)view;
        check(menu != nil && menu.numberOfItems == 2, "named filter dropdown");
        check([menu.itemTitles isEqualToArray:@[@"Images", @"Any"]], "filter group names");
        [menu selectItemAtIndex:1];
        [NSApp sendAction:menu.action to:menu.target from:menu];
        check(panel.allowedFileTypes == nil && panel.allowsOtherFileTypes, "wildcard filter");
#pragma clang diagnostic pop
    }
    if (expectedKind == 3)
        check([panel.nameFieldStringValue isEqualToString:@"probe-ñ.png"], "UTF-8 default filename");
    [panel cancel:nil];
}

static void scheduleCancel(NSSavePanel *panel) {
    NSTimer *timer = [NSTimer timerWithTimeInterval:0.25 repeats:NO block:^(NSTimer *unused) {
        (void)unused;
        checkAndCancel(panel);
    }];
    [[NSRunLoop mainRunLoop] addTimer:timer forMode:NSDefaultRunLoopMode];
    [[NSRunLoop mainRunLoop] addTimer:timer forMode:NSModalPanelRunLoopMode];
}

@implementation NSOpenPanel (FBProbe)
+ (NSOpenPanel *)fbProbeOpenPanel {
    NSOpenPanel *panel = [self fbProbeOpenPanel];
    scheduleCancel(panel);
    return panel;
}
@end
@implementation NSSavePanel (FBProbe)
+ (NSSavePanel *)fbProbeSavePanel {
    NSSavePanel *panel = [self fbProbeSavePanel];
    scheduleCancel(panel);
    return panel;
}
@end

static void callback(const char *result) {
    check([NSThread isMainThread], "async callback on Cocoa main thread");
    check(result != NULL && result[0] == '\0', "non-null empty cancellation callback");
    callbackDone = YES;
}

static void waitForCallback(void) {
    NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:10];
    while (!callbackDone && [deadline timeIntervalSinceNow] > 0)
        [[NSRunLoop mainRunLoop] runMode:NSDefaultRunLoopMode
                             beforeDate:[NSDate dateWithTimeIntervalSinceNow:0.05]];
    check(callbackDone, "async callback completed within deadline");
    callbackDone = NO;
}

int main(void) {
    @autoreleasepool {
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [NSApp finishLaunching];
        method_exchangeImplementations(class_getClassMethod([NSOpenPanel class], @selector(openPanel)),
            class_getClassMethod([NSOpenPanel class], @selector(fbProbeOpenPanel)));
        method_exchangeImplementations(class_getClassMethod([NSSavePanel class], @selector(savePanel)),
            class_getClassMethod([NSSavePanel class], @selector(fbProbeSavePanel)));
        DialogInit();
        expectedKind = 1;
        expectedMultiple = YES;
        const char *result = DialogOpenFilePanel("File dialog test files ñ", "/tmp", "Images;png,jpg|Any;*", 1);
        check(result && !result[0], "sync file cancel result");
        expectedKind = 2;
        expectedMultiple = NO;
        result = DialogOpenFolderPanel("File dialog test folders ñ", "/tmp", 0);
        check(result && !result[0], "sync folder cancel result");
        expectedKind = 3;
        result = DialogSaveFilePanel("File dialog test save ñ", "/tmp", "probe-ñ.png", "Images;png,jpg|Any;*");
        check(result && !result[0], "sync save cancel result");
        expectedKind = 1;
        expectedMultiple = NO;
        DialogOpenFilePanelAsync("File dialog test async files ñ", "/tmp", "Images;png,jpg|Any;*", 0, callback);
        waitForCallback();
        expectedKind = 2;
        expectedMultiple = YES;
        DialogOpenFolderPanelAsync("File dialog test async folders ñ", "/tmp", 1, callback);
        waitForCallback();
        expectedKind = 3;
        DialogSaveFilePanelAsync("File dialog test async save ñ", "/tmp", "probe-ñ.png", "Images;png,jpg|Any;*", callback);
        waitForCallback();
        check(observedPanels == 6, "all six dialog entry points exercised");
        DialogOpenFilePanelAsync(NULL, NULL, NULL, 0, NULL);
        printf("PASS: %lu assertions; six real Cocoa dialogs cancelled automatically.\n", checks);
    }
    return 0;
}
