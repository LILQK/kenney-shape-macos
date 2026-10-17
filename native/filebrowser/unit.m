/* Include the implementation to exercise private parsing and result formatting
 * without adding testing exports to the shipped library. */
#include "FileBrowser.m"
#include <stdio.h>
#include <stdlib.h>

static unsigned checks = 0;
static void check(BOOL condition, const char *message) {
    checks++;
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        exit(1);
    }
}

@interface FBResultDouble : NSObject
@property(nonatomic) BOOL openPanel;
@property(nonatomic, copy) NSArray<NSURL *> *URLs;
@property(nonatomic, strong) NSURL *URL;
@end
@implementation FBResultDouble
- (BOOL)isKindOfClass:(Class)classType {
    if (classType == [NSOpenPanel class]) return self.openPanel;
    return [super isKindOfClass:classType];
}
@end

int main(void) {
    @autoreleasepool {
        check([FBString(NULL) isEqualToString:@""], "null native string");
        check([FBString("ñ-日本語") isEqualToString:@"ñ-日本語"], "native UTF-8 string");
        check(FBFilters(@"").count == 0, "empty filter list");
        NSArray<FBFilter *> *filters = FBFilters(@"Images;png,jpg|All;*");
        check(filters.count == 2, "two named filter groups");
        check([filters[0].name isEqualToString:@"Images"], "filter group name");
        check([filters[0].extensions isEqualToArray:@[@"png", @"jpg"]], "extension list");
        check(filters[1].extensions == nil, "asterisk wildcard");
        check(FBFilters(@"All;*.*")[0].extensions == nil, "star dot star wildcard");
        check(FBFilters(@"All;")[0].extensions == nil, "empty extensions allow all");
        check([FBFilters(@"Images; *.png, .jpg,png, ")[0].extensions
            isEqualToArray:@[@"png", @"jpg"]], "normalize and deduplicate extensions");
        FBResultDouble *panel = [FBResultDouble new];
        panel.openPanel = YES;
        panel.URLs = @[[NSURL fileURLWithPath:@"/tmp/one ñ.png"],
                       [NSURL fileURLWithPath:@"/tmp/二.png"],
                       [NSURL URLWithString:@"https://example.com/not-a-file"]];
        check([[FBResult((NSSavePanel *)panel, NSModalResponseOK) precomposedStringWithCanonicalMapping]
            isEqualToString:@"/tmp/one ñ.png\x1c/tmp/二.png"], "U+001C multiple selection UTF-8 paths");
        check([FBResult((NSSavePanel *)panel, NSModalResponseCancel)
            isEqualToString:@""], "cancel ignores selected URLs");
        panel.openPanel = NO;
        panel.URL = [NSURL fileURLWithPath:@"/tmp/save ñ.shape"];
        check([[FBResult((NSSavePanel *)panel, NSModalResponseOK) precomposedStringWithCanonicalMapping]
            isEqualToString:@"/tmp/save ñ.shape"], "save returns native filesystem path");
        panel.URL = nil;
        check([FBResult((NSSavePanel *)panel, NSModalResponseOK)
            isEqualToString:@""], "missing save URL is an empty string");
        printf("PASS: %u parsing and result-format assertions.\n", checks);
    }
    return 0;
}
