import re, os, json
files = [
    'repos/playwright/browser_patches/winldd/PrintDeps.cpp',
    'repos/playwright/browser_patches/webkit/embedder/Playwright/win/WebKitBrowserWindow.cpp',
    'repos/playwright/browser_patches/webkit/embedder/Playwright/win/MainWindow.cpp',
    'repos/playwright/browser_patches/webkit/embedder/Playwright/win/Common.cpp',
    'repos/playwright/browser_patches/webkit/embedder/Playwright/win/WinMain.cpp',
]
apis = ['LoadLibraryEx','GetModuleFileName','ImageDirectoryEntryToData','FormatMessage','SetDllDirectoryA','FreeLibrary','LocalFree','CreateWindowEx','RegisterClassEx','SendMessage','GetWindowRect','SetWindowText','PostMessage','GetClientRect','MoveWindow','ShowWindow','GetMenu','SetMenu','DestroyMenu','SetFocus','GetClassName','LoadString','LoadIcon','LoadCursor','CreateFont','DeleteObject','SetWindowLongPtr','GetWindowLongPtr','DefWindowProc','CallWindowProc','DialogBox','EndDialog','PathFileExists','PathIsUNC','UrlCreateFromPath','SetWindowPos']
counts = {}
for f in files:
    text = open(f, encoding='utf-8', errors='ignore').read()
    for api in apis:
        counts[api] = counts.get(api,0) + len(re.findall(r'\b'+api+r'\b', text))
print(json.dumps({k:v for k,v in counts.items() if v>0}, indent=2))
