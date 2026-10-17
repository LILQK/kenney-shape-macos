#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Mono's default P/Invoke bool marshalling uses a four-byte BOOL. UTF-8 strings. */
typedef void (*FileBrowserCallback)(const char *path);
void DialogInit(void);
const char *DialogOpenFilePanel(const char *title, const char *directory,
                                const char *extension, int32_t multiselect);
const char *DialogOpenFolderPanel(const char *title, const char *directory,
                                  int32_t multiselect);
const char *DialogSaveFilePanel(const char *title, const char *directory,
                                const char *defaultName, const char *extension);
void DialogOpenFilePanelAsync(const char *title, const char *directory,
                              const char *extension, int32_t multiselect,
                              FileBrowserCallback callback);
void DialogOpenFolderPanelAsync(const char *title, const char *directory,
                                int32_t multiselect, FileBrowserCallback callback);
void DialogSaveFilePanelAsync(const char *title, const char *directory,
                              const char *defaultName, const char *extension,
                              FileBrowserCallback callback);

#ifdef __cplusplus
}
#endif
