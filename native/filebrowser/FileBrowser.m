#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
#include "FileBrowser.h"

/* This is an ABI-compatible macOS implementation of the seven entry points
 * imported by the Crosstales.FB.Wrapper.Linux.NativeMethods. */

static NSString *FBString(const char *value) {
    if (!value) return @"";
    NSString *text = [NSString stringWithUTF8String:value];
    return text ?: @"";
}

static void FBMain(void (^work)(void)) {
    if ([NSThread isMainThread]) work();
    else dispatch_sync(dispatch_get_main_queue(), work);
}

@interface FBFilter : NSObject
@property(nonatomic, copy) NSString *name;
@property(nonatomic, copy) NSArray<NSString *> *extensions;
@end
@implementation FBFilter
@end

/* Producer format: Label;ext,ext|Other label;ext. Empty or '*' means any type. */
static NSArray<FBFilter *> *FBFilters(NSString *specification) {
    NSMutableArray<FBFilter *> *filters = [NSMutableArray array];
    for (NSString *group in [specification componentsSeparatedByString:@"|"]) {
        if (!group.length) continue;
        NSRange separator = [group rangeOfString:@";"];
        NSString *name = separator.location == NSNotFound ? group :
            [group substringToIndex:separator.location];
        NSString *list = separator.location == NSNotFound ? group :
            [group substringFromIndex:separator.location + 1];
        NSMutableArray<NSString *> *extensions = [NSMutableArray array];
        BOOL all = NO;
        for (NSString *item in [list componentsSeparatedByString:@","]) {
            NSString *extension = [item stringByTrimmingCharactersInSet:
                [NSCharacterSet whitespaceAndNewlineCharacterSet]];
            if ([extension isEqualToString:@"*"] ||
                [extension isEqualToString:@"*.*"]) {
                all = YES;
                break;
            }
            if ([extension hasPrefix:@"*."]) extension = [extension substringFromIndex:2];
            else if ([extension hasPrefix:@"."]) extension = [extension substringFromIndex:1];
            if (extension.length && ![extensions containsObject:extension])
                [extensions addObject:extension];
        }
        FBFilter *filter = [FBFilter new];
        filter.name = name.length ? name : @"Files";
        filter.extensions = all || extensions.count == 0 ? nil : extensions;
        [filters addObject:filter];
    }
    return filters;
}

@interface FBFilterSelector : NSObject
@property(nonatomic, weak) NSSavePanel *panel;
@property(nonatomic, copy) NSArray<FBFilter *> *filters;
- (void)select:(NSPopUpButton *)sender;
@end
@implementation FBFilterSelector
- (void)select:(NSPopUpButton *)sender {
    NSInteger index = [sender indexOfSelectedItem];
    if (index < 0 || (NSUInteger)index >= self.filters.count) return;
    FBFilter *filter = self.filters[(NSUInteger)index];
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    self.panel.allowedFileTypes = filter.extensions;
#pragma clang diagnostic pop
    self.panel.allowsOtherFileTypes = filter.extensions == nil;
}
@end

static char FBFilterKey;

static void FBApplyFilters(NSSavePanel *panel, NSString *specification) {
    NSArray<FBFilter *> *filters = FBFilters(specification);
    if (filters.count == 0) return;
    FBFilterSelector *selector = [FBFilterSelector new];
    selector.panel = panel;
    selector.filters = filters;
    NSPopUpButton *menu = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(74, 4, 246, 26)
                                                                  pullsDown:NO];
    for (FBFilter *filter in filters) [menu addItemWithTitle:filter.name];
    [selector select:menu];
    if (filters.count > 1) {
        NSView *accessory = [[NSView alloc] initWithFrame:NSMakeRect(0, 0, 328, 34)];
        NSTextField *label = [[NSTextField alloc] initWithFrame:NSMakeRect(0, 7, 70, 20)];
        label.stringValue = @"Format:";
        label.bezeled = NO;
        label.drawsBackground = NO;
        label.editable = NO;
        label.selectable = NO;
        menu.target = selector;
        menu.action = @selector(select:);
        [accessory addSubview:label];
        [accessory addSubview:menu];
        panel.accessoryView = accessory;
        if ([panel isKindOfClass:[NSOpenPanel class]])
            ((NSOpenPanel *)panel).accessoryViewDisclosed = YES;
        /* Cocoa does not retain a control's target. Keep it for the panel lifetime. */
        objc_setAssociatedObject(panel, &FBFilterKey, selector, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
    }
}

static void FBConfigure(NSSavePanel *panel, NSString *title, NSString *directory) {
    [NSApplication sharedApplication];
    if (title.length) {
        panel.title = title;
        panel.message = title;
    }
    if (directory.length)
        panel.directoryURL = [NSURL fileURLWithPath:[directory stringByExpandingTildeInPath]
                                      isDirectory:YES];
    panel.canCreateDirectories = YES;
    panel.extensionHidden = NO;
}

static NSOpenPanel *FBOpen(NSString *title, NSString *directory,
                           NSString *extension, BOOL folders, BOOL multiple) {
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    FBConfigure(panel, title, directory);
    panel.canChooseFiles = !folders;
    panel.canChooseDirectories = folders;
    panel.allowsMultipleSelection = multiple;
    panel.resolvesAliases = YES;
    if (!folders) FBApplyFilters(panel, extension);
    return panel;
}

static NSSavePanel *FBSave(NSString *title, NSString *directory,
                           NSString *defaultName, NSString *extension) {
    NSSavePanel *panel = [NSSavePanel savePanel];
    FBConfigure(panel, title, directory);
    if (defaultName.length) panel.nameFieldStringValue = defaultName;
    FBApplyFilters(panel, extension);
    return panel;
}

static NSString *FBResult(NSSavePanel *panel, NSModalResponse response) {
    if (response != NSModalResponseOK) return @"";
    if ([panel isKindOfClass:[NSOpenPanel class]]) {
        NSMutableArray<NSString *> *paths = [NSMutableArray array];
        for (NSURL *url in ((NSOpenPanel *)panel).URLs) {
            if (url.isFileURL && url.path) [paths addObject:url.path];
        }
        /* U+001C is the exact separator used by the managed Linux wrapper. */
        return [paths componentsJoinedByString:@"\x1c"];
    }
    return panel.URL.path ?: @"";
}

/* The managed synchronous wrapper immediately copies this pointer. Each caller
 * thread owns its buffer until its next synchronous dialog on that thread. */
static pthread_key_t FBReturnKey;
static pthread_once_t FBReturnKeyOnce = PTHREAD_ONCE_INIT;
static void FBCreateReturnKey(void) {
    pthread_key_create(&FBReturnKey, free);
}
static const char *FBSync(NSSavePanel *(^createPanel)(void)) {
    @autoreleasepool {
        __block NSString *result = @"";
        FBMain(^{
            NSSavePanel *panel = createPanel();
            NSModalResponse response = [panel runModal];
            result = FBResult(panel, response);
        });
        pthread_once(&FBReturnKeyOnce, FBCreateReturnKey);
        char *next = strdup(result.UTF8String ?: "");
        free(pthread_getspecific(FBReturnKey));
        pthread_setspecific(FBReturnKey, next);
        return next ?: "";
    }
}

static void FBAsync(NSSavePanel *(^createPanel)(void), FileBrowserCallback callback) {
    if (!callback) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        @autoreleasepool {
            NSSavePanel *panel = createPanel();
            [panel beginWithCompletionHandler:^(NSModalResponse response) {
                @autoreleasepool {
                    NSString *result = FBResult(panel, response);
                    /* LPStr is borrowed only for the duration of this callback. */
                    callback(result.UTF8String ?: "");
                }
            }];
        }
    });
}

__attribute__((visibility("default"))) void DialogInit(void) {
    FBMain(^{ [NSApplication sharedApplication]; });
}

__attribute__((visibility("default"))) const char *DialogOpenFilePanel(
    const char *title, const char *directory, const char *extension, int32_t multiselect) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory), *e = FBString(extension);
        return FBSync(^{ return FBOpen(t, d, e, NO, multiselect != 0); });
    }
}

__attribute__((visibility("default"))) const char *DialogOpenFolderPanel(
    const char *title, const char *directory, int32_t multiselect) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory);
        return FBSync(^{ return FBOpen(t, d, @"", YES, multiselect != 0); });
    }
}

__attribute__((visibility("default"))) const char *DialogSaveFilePanel(
    const char *title, const char *directory, const char *defaultName, const char *extension) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory);
        NSString *n = FBString(defaultName), *e = FBString(extension);
        return FBSync(^{ return FBSave(t, d, n, e); });
    }
}

__attribute__((visibility("default"))) void DialogOpenFilePanelAsync(
    const char *title, const char *directory, const char *extension,
    int32_t multiselect, FileBrowserCallback callback) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory), *e = FBString(extension);
        FBAsync(^{ return FBOpen(t, d, e, NO, multiselect != 0); }, callback);
    }
}

__attribute__((visibility("default"))) void DialogOpenFolderPanelAsync(
    const char *title, const char *directory, int32_t multiselect, FileBrowserCallback callback) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory);
        FBAsync(^{ return FBOpen(t, d, @"", YES, multiselect != 0); }, callback);
    }
}

__attribute__((visibility("default"))) void DialogSaveFilePanelAsync(
    const char *title, const char *directory, const char *defaultName,
    const char *extension, FileBrowserCallback callback) {
    @autoreleasepool {
        NSString *t = FBString(title), *d = FBString(directory);
        NSString *n = FBString(defaultName), *e = FBString(extension);
        FBAsync(^{ return FBSave(t, d, n, e); }, callback);
    }
}
