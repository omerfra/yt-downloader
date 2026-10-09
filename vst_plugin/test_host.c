/*
 * Minimal VST2 test host for the YouTube Downloader plugin (development only).
 *
 * Loads the plugin DLL, checks audio pass-through, then opens the editor,
 * closes it, reopens it and finally removes the plugin - saving a screenshot
 * of the editor window after each open.
 *
 * Usage: test_host.exe "<plugin.dll>" <screenshot-prefix>
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#include <windows.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "vst2_abi.h"

typedef AEffect *(*PluginEntry)(audioMasterCallback);

static intptr_t host_callback(AEffect *e, int32_t opcode, int32_t index, intptr_t value,
                              void *ptr, float opt)
{
    (void)e; (void)index; (void)value; (void)ptr; (void)opt;
    return opcode == audioMasterVersion ? 2400 : 0;
}

static void pump(DWORD ms)
{
    DWORD end = GetTickCount() + ms;
    while ((LONG)(end - GetTickCount()) > 0) {
        MSG msg;
        while (PeekMessageW(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        Sleep(10);
    }
}

static BOOL CALLBACK count_child(HWND hwnd, LPARAM count)
{
    (void)hwnd;
    (*(int *)count)++;
    return TRUE;
}

static void save_screenshot(HWND hwnd, const char *path)
{
    /* Copy from the screen: PrintWindow doesn't render other processes' child windows. */
    RECT rc;
    GetClientRect(hwnd, &rc);
    int w = rc.right, h = rc.bottom;
    POINT origin = {0, 0};
    ClientToScreen(hwnd, &origin);
    HDC wdc = GetDC(NULL);
    HDC mdc = CreateCompatibleDC(wdc);
    HBITMAP bmp = CreateCompatibleBitmap(wdc, w, h);
    SelectObject(mdc, bmp);
    BitBlt(mdc, 0, 0, w, h, wdc, origin.x, origin.y, SRCCOPY);

    BITMAPINFOHEADER bi = {sizeof(bi), w, h, 1, 32, BI_RGB, 0, 0, 0, 0, 0};
    DWORD size = (DWORD)w * h * 4;
    void *pixels = malloc(size);
    GetDIBits(mdc, bmp, 0, h, pixels, (BITMAPINFO *)&bi, DIB_RGB_COLORS);
    BITMAPFILEHEADER bf = {0x4D42, sizeof(bf) + sizeof(bi) + size, 0, 0, sizeof(bf) + sizeof(bi)};
    FILE *f = fopen(path, "wb");
    if (f) {
        fwrite(&bf, sizeof(bf), 1, f);
        fwrite(&bi, sizeof(bi), 1, f);
        fwrite(pixels, size, 1, f);
        fclose(f);
        printf("  screenshot: %s\n", path);
    }
    free(pixels);
    DeleteObject(bmp);
    DeleteDC(mdc);
    ReleaseDC(NULL, wdc);
}

static HWND open_editor(AEffect *e, const char *shot)
{
    ERect *r = NULL;
    e->dispatcher(e, effEditGetRect, 0, 0, &r, 0);
    int w = r ? r->right - r->left : 400, h = r ? r->bottom - r->top : 300;
    RECT wr = {0, 0, w, h};
    AdjustWindowRect(&wr, WS_OVERLAPPEDWINDOW, FALSE);
    HWND win = CreateWindowW(L"STATIC", L"VST test host", WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                             100, 100, wr.right - wr.left, wr.bottom - wr.top, NULL, NULL,
                             GetModuleHandleW(NULL), NULL);
    SetWindowPos(win, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE);
    intptr_t ok = e->dispatcher(e, effEditOpen, 0, 0, win, 0);
    printf("  effEditOpen -> %d (editor %dx%d)\n", (int)ok, w, h);
    pump(6000);
    int children = 0;
    EnumChildWindows(win, count_child, (LPARAM)&children);
    printf("  %d child windows (container + embedded Tk widgets)\n", children);
    save_screenshot(win, shot);
    return win;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        printf("usage: test_host <plugin.dll> <screenshot-prefix>\n");
        return 2;
    }
    SetProcessDPIAware(); /* so screen captures line up on scaled displays */
    HMODULE dll = LoadLibraryA(argv[1]);
    if (!dll) {
        printf("FAIL: LoadLibrary error %lu\n", GetLastError());
        return 1;
    }
    PluginEntry entry = (PluginEntry)GetProcAddress(dll, "VSTPluginMain");
    PluginEntry legacy = (PluginEntry)GetProcAddress(dll, "main");
    printf("exports: VSTPluginMain=%p main=%p\n", (void *)entry, (void *)legacy);
    if (!entry || entry != legacy) {
        printf("FAIL: missing exports\n");
        return 1;
    }

    AEffect *e = entry(host_callback);
    if (!e || e->magic != VST_MAGIC) {
        printf("FAIL: bad AEffect\n");
        return 1;
    }
    char name[64] = {0}, vendor[64] = {0};
    e->dispatcher(e, effOpen, 0, 0, NULL, 0);
    e->dispatcher(e, effGetEffectName, 0, 0, name, 0);
    e->dispatcher(e, effGetVendorString, 0, 0, vendor, 0);
    printf("plugin: '%s' by '%s', in=%d out=%d flags=0x%x id=0x%x\n", name, vendor,
           e->numInputs, e->numOutputs, e->flags, e->uniqueID);

    /* Audio pass-through check */
    float inL[512], inR[512], outL[512], outR[512];
    for (int i = 0; i < 512; i++) {
        inL[i] = sinf(i * 0.05f);
        inR[i] = cosf(i * 0.05f);
        outL[i] = outR[i] = 99.0f;
    }
    float *ins[2] = {inL, inR}, *outs[2] = {outL, outR};
    e->dispatcher(e, effSetSampleRate, 0, 0, NULL, 48000.0f);
    e->dispatcher(e, effMainsChanged, 0, 1, NULL, 0);
    e->processReplacing(e, ins, outs, 512);
    int pass = memcmp(inL, outL, sizeof(inL)) == 0 && memcmp(inR, outR, sizeof(inR)) == 0;
    printf("audio pass-through: %s\n", pass ? "OK" : "FAIL");

    char shot[MAX_PATH];
    printf("open #1\n");
    snprintf(shot, MAX_PATH, "%s1.bmp", argv[2]);
    HWND w1 = open_editor(e, shot);
    e->dispatcher(e, effEditClose, 0, 0, NULL, 0);
    DestroyWindow(w1);
    printf("closed editor; app should keep running\n");
    pump(1500);

    printf("open #2\n");
    snprintf(shot, MAX_PATH, "%s2.bmp", argv[2]);
    HWND w2 = open_editor(e, shot);
    e->dispatcher(e, effEditClose, 0, 0, NULL, 0);
    DestroyWindow(w2);

    DWORD t0 = GetTickCount();
    e->dispatcher(e, effMainsChanged, 0, 0, NULL, 0);
    e->dispatcher(e, effClose, 0, 0, NULL, 0);
    printf("effClose took %lu ms\n", GetTickCount() - t0);
    FreeLibrary(dll);
    printf("done\n");
    return pass ? 0 : 1;
}
