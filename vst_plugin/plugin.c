/*
 * YouTube Downloader - VST2 plugin wrapper
 *
 * A stereo pass-through effect whose editor window hosts the real
 * "YouTube Downloader.exe" GUI. When the editor opens, the plugin starts the
 * app with "--embed <hwnd>" and Tkinter embeds itself into our window using
 * Tk's container protocol (see tk/win/tkWinEmbed.c).
 *
 * The app keeps running while the editor is closed (so downloads continue);
 * its window is parked in a hidden top-level window until the editor reopens.
 * It is shut down when the plugin instance is removed, and a job object kills
 * it if the DAW exits or crashes.
 */

#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#include "vst2_abi.h"

#define PLUGIN_NAME "YouTube Downloader"
#define PLUGIN_VENDOR "omerfra"
#define PLUGIN_UNIQUE_ID 0x5974446C /* 'YtDl' */
#define PLUGIN_VERSION 1000

#define APP_EXE_NAME L"YouTube Downloader.exe"
/* Optional override of the command used to start the app (development):
 * e.g. set YTDL_VST_APP=pythonw "C:\path\yt_downloader_gui.py" */
#define APP_OVERRIDE_ENV L"YTDL_VST_APP"

#define EDITOR_WIDTH 680
#define EDITOR_HEIGHT 580
#define SHUTDOWN_GRACE_MS 1500
#define STATUS_TIMER_ID 1

/* Tk embedding protocol messages (tk/win/tkWin.h). */
#define TK_CLAIMFOCUS (WM_USER)
#define TK_GEOMETRYREQ (WM_USER + 1)
#define TK_ATTACHWINDOW (WM_USER + 2)
#define TK_DETACHWINDOW (WM_USER + 3)
#define TK_GETFRAMEWID (WM_USER + 9)
#define TK_INFO (WM_USER + 13)
#define TK_CONTAINER_VERIFY 0x01
#define TK_CONTAINER_ISAVAILABLE 0x02

static const WCHAR CONTAINER_CLASS[] = L"YtdlVstContainer";
static const WCHAR PARKING_CLASS[] = L"YtdlVstParking";

typedef struct Plugin {
    AEffect effect;
    audioMasterCallback host;
    ERect rect;
    HWND parking;   /* hidden top-level that holds the container while the editor is closed */
    HWND container; /* child window the Tk app embeds itself into */
    HWND embedded;  /* the Tk app's window, once attached */
    HANDLE process;
    HANDLE job;
    WCHAR status[512]; /* shown in the container while the app isn't attached */
} Plugin;

static HINSTANCE g_instance;
static LONG g_classes_registered;

/* ------------------------------------------------------------------------- */
/* Helpers                                                                   */
/* ------------------------------------------------------------------------- */

static void copy_string(void *dst, const char *src, size_t max_len)
{
    strncpy((char *)dst, src, max_len - 1);
    ((char *)dst)[max_len - 1] = '\0';
}

static int app_running(Plugin *p)
{
    return p->process && WaitForSingleObject(p->process, 0) == WAIT_TIMEOUT;
}

static void set_status(Plugin *p, const WCHAR *text)
{
    wcsncpy(p->status, text, 511);
    p->status[511] = L'\0';
    if (p->container)
        InvalidateRect(p->container, NULL, TRUE);
}

static void fit_embedded(Plugin *p)
{
    RECT rc;
    if (!p->embedded)
        return;
    GetClientRect(p->container, &rc);
    SetWindowPos(p->embedded, NULL, 0, 0, rc.right, rc.bottom,
                 SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS);
}

/* Directory containing this DLL, with a trailing backslash. */
static void get_plugin_dir(WCHAR *out, DWORD size)
{
    DWORD len = GetModuleFileNameW(g_instance, out, size);
    if (len == 0 || len >= size) {
        out[0] = L'\0';
        return;
    }
    WCHAR *slash = wcsrchr(out, L'\\');
    if (slash)
        slash[1] = L'\0';
}

/* ------------------------------------------------------------------------- */
/* App process                                                               */
/* ------------------------------------------------------------------------- */

static void release_process(Plugin *p)
{
    if (p->process) {
        CloseHandle(p->process);
        p->process = NULL;
    }
    p->embedded = NULL;
}

static void launch_app(Plugin *p)
{
    WCHAR base[MAX_PATH * 2];
    WCHAR cmd[MAX_PATH * 2 + 64];

    if (app_running(p))
        return;
    release_process(p);

    DWORD env_len = GetEnvironmentVariableW(APP_OVERRIDE_ENV, base, MAX_PATH * 2);
    if (env_len == 0 || env_len >= MAX_PATH * 2) {
        WCHAR dir[MAX_PATH], exe[MAX_PATH + 32];
        get_plugin_dir(dir, MAX_PATH);
        _snwprintf(exe, MAX_PATH + 32, L"%ls%ls", dir, APP_EXE_NAME);
        exe[MAX_PATH + 31] = L'\0';
        if (GetFileAttributesW(exe) == INVALID_FILE_ATTRIBUTES) {
            WCHAR msg[512];
            _snwprintf(msg, 512,
                       L"Could not find \"%ls\".\n\nPut it in the same folder as the plugin:\n%ls",
                       APP_EXE_NAME, dir);
            msg[511] = L'\0';
            set_status(p, msg);
            return;
        }
        _snwprintf(base, MAX_PATH * 2, L"\"%ls\"", exe);
        base[MAX_PATH * 2 - 1] = L'\0';
    }

    _snwprintf(cmd, MAX_PATH * 2 + 64, L"%ls --embed 0x%llX", base,
               (unsigned long long)(uintptr_t)p->container);
    cmd[MAX_PATH * 2 + 63] = L'\0';

    if (!p->job) {
        /* Kill the app (and its yt-dlp/ffmpeg children) if the DAW goes away. */
        p->job = CreateJobObjectW(NULL, NULL);
        if (p->job) {
            JOBOBJECT_EXTENDED_LIMIT_INFORMATION info;
            ZeroMemory(&info, sizeof(info));
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(p->job, JobObjectExtendedLimitInformation, &info,
                                    sizeof(info));
        }
    }

    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_SUSPENDED, NULL, NULL, &si, &pi)) {
        WCHAR msg[512];
        _snwprintf(msg, 512, L"Failed to start the downloader (error %lu).\n\n%ls",
                   GetLastError(), cmd);
        msg[511] = L'\0';
        set_status(p, msg);
        return;
    }
    if (p->job)
        AssignProcessToJobObject(p->job, pi.hProcess);
    ResumeThread(pi.hThread);
    CloseHandle(pi.hThread);
    p->process = pi.hProcess;
    set_status(p, L"Starting YouTube Downloader...");
}

/* ------------------------------------------------------------------------- */
/* Windows                                                                   */
/* ------------------------------------------------------------------------- */

static LRESULT CALLBACK container_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    Plugin *p = (Plugin *)GetWindowLongPtrW(hwnd, GWLP_USERDATA);
    if (!p)
        return DefWindowProcW(hwnd, msg, wp, lp);

    switch (msg) {
    /* --- Tk container protocol --- */
    case TK_INFO:
        if (wp == TK_CONTAINER_VERIFY)
            return (LRESULT)(int)(intptr_t)hwnd;
        if (wp == TK_CONTAINER_ISAVAILABLE)
            return p->embedded == NULL;
        return 0;
    case TK_ATTACHWINDOW:
        if (p->embedded && IsWindow(p->embedded))
            return 0;
        if (wp) {
            p->embedded = (HWND)wp;
            fit_embedded(p);
        }
        return (LRESULT)(int)(intptr_t)hwnd;
    case TK_DETACHWINDOW:
        p->embedded = NULL;
        InvalidateRect(hwnd, NULL, TRUE);
        return 1;
    case TK_GEOMETRYREQ:
        /* The editor has a fixed size; keep the app filling it. */
        fit_embedded(p);
        return 1;
    case TK_CLAIMFOCUS:
        if (p->embedded)
            SetFocus(p->embedded);
        return 1;
    case TK_GETFRAMEWID:
        return (LRESULT)GetAncestor(hwnd, GA_ROOT);

    /* --- Regular window messages --- */
    case WM_SIZE:
        fit_embedded(p);
        return 0;
    case WM_SETFOCUS:
        if (p->embedded)
            SetFocus(p->embedded);
        return 0;
    case WM_TIMER:
        if (wp == STATUS_TIMER_ID) {
            if (p->embedded && !IsWindow(p->embedded)) {
                p->embedded = NULL;
                InvalidateRect(hwnd, NULL, TRUE);
            }
            if (!p->embedded && p->process && !app_running(p)) {
                release_process(p);
                set_status(p, L"YouTube Downloader has exited.\n\n"
                              L"Close and reopen this window to restart it.");
            }
        }
        return 0;
    case WM_ERASEBKGND:
        return 1;
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(hwnd, &ps);
        RECT rc;
        GetClientRect(hwnd, &rc);
        HBRUSH bg = CreateSolidBrush(RGB(30, 30, 30));
        FillRect(dc, &rc, bg);
        DeleteObject(bg);
        if (!p->embedded) {
            SetBkMode(dc, TRANSPARENT);
            SetTextColor(dc, RGB(220, 220, 220));
            SelectObject(dc, GetStockObject(DEFAULT_GUI_FONT));
            InflateRect(&rc, -24, -24);
            RECT measure = rc;
            DrawTextW(dc, p->status, -1, &measure, DT_CENTER | DT_WORDBREAK | DT_EDITCONTROL | DT_CALCRECT);
            int h = measure.bottom - measure.top;
            rc.top += (rc.bottom - rc.top - h) / 2;
            DrawTextW(dc, p->status, -1, &rc, DT_CENTER | DT_WORDBREAK | DT_EDITCONTROL);
        }
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_DESTROY:
        KillTimer(hwnd, STATUS_TIMER_ID);
        p->container = NULL;
        p->embedded = NULL;
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static LRESULT CALLBACK parking_proc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp)
{
    if (msg == WM_DESTROY) {
        Plugin *p = (Plugin *)GetWindowLongPtrW(hwnd, GWLP_USERDATA);
        if (p)
            p->parking = NULL;
        return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static int register_classes(void)
{
    if (InterlockedCompareExchange(&g_classes_registered, 1, 0) != 0)
        return 1;

    WNDCLASSEXW wc;
    ZeroMemory(&wc, sizeof(wc));
    wc.cbSize = sizeof(wc);
    wc.hInstance = g_instance;
    wc.hCursor = LoadCursorW(NULL, (LPCWSTR)IDC_ARROW);

    wc.lpfnWndProc = container_proc;
    wc.lpszClassName = CONTAINER_CLASS;
    if (!RegisterClassExW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
        return 0;

    wc.lpfnWndProc = parking_proc;
    wc.lpszClassName = PARKING_CLASS;
    if (!RegisterClassExW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
        return 0;
    return 1;
}

static int ensure_windows(Plugin *p)
{
    if (!register_classes())
        return 0;
    if (!p->parking) {
        p->parking = CreateWindowExW(WS_EX_TOOLWINDOW, PARKING_CLASS, L"", WS_POPUP, 0, 0,
                                     EDITOR_WIDTH, EDITOR_HEIGHT, NULL, NULL, g_instance, NULL);
        if (!p->parking)
            return 0;
        SetWindowLongPtrW(p->parking, GWLP_USERDATA, (LONG_PTR)p);
    }
    if (!p->container) {
        p->container = CreateWindowExW(0, CONTAINER_CLASS, L"", WS_CHILD | WS_CLIPCHILDREN, 0, 0,
                                       EDITOR_WIDTH, EDITOR_HEIGHT, p->parking, NULL, g_instance,
                                       NULL);
        if (!p->container)
            return 0;
        SetWindowLongPtrW(p->container, GWLP_USERDATA, (LONG_PTR)p);
        SetTimer(p->container, STATUS_TIMER_ID, 500, NULL);
    }
    return 1;
}

static int editor_open(Plugin *p, HWND parent)
{
    if (!parent || !ensure_windows(p))
        return 0;
    SetParent(p->container, parent);
    SetWindowPos(p->container, HWND_TOP, 0, 0, EDITOR_WIDTH, EDITOR_HEIGHT, SWP_SHOWWINDOW);
    launch_app(p);
    fit_embedded(p);
    return 1;
}

static void editor_close(Plugin *p)
{
    if (!p->container)
        return;
    /* Keep the app (and any running download) alive while the editor is closed. */
    ShowWindow(p->container, SW_HIDE);
    SetParent(p->container, p->parking);
}

static void plugin_destroy(Plugin *p)
{
    /* Destroying our windows destroys the embedded Tk window, which makes the
     * app save its preferences and exit on its own. */
    if (p->parking) {
        DWORD owner = GetWindowThreadProcessId(p->parking, NULL);
        if (owner == GetCurrentThreadId()) {
            DestroyWindow(p->parking);
        } else {
            /* Wrong thread to destroy them: detach from p (freed below) and
             * let the GUI thread tear the windows down. */
            if (p->container)
                SetWindowLongPtrW(p->container, GWLP_USERDATA, 0);
            SetWindowLongPtrW(p->parking, GWLP_USERDATA, 0);
            PostMessageW(p->parking, WM_CLOSE, 0, 0);
        }
    }
    if (p->process) {
        if (WaitForSingleObject(p->process, SHUTDOWN_GRACE_MS) == WAIT_TIMEOUT)
            TerminateProcess(p->process, 0);
        release_process(p);
    }
    if (p->job)
        CloseHandle(p->job); /* kills anything still left in the job */
    free(p);
}

/* ------------------------------------------------------------------------- */
/* VST2 callbacks                                                            */
/* ------------------------------------------------------------------------- */

static intptr_t dispatcher(AEffect *effect, int32_t opcode, int32_t index, intptr_t value,
                           void *ptr, float opt)
{
    Plugin *p = (Plugin *)effect->object;
    (void)index;
    (void)value;
    (void)opt;

    switch (opcode) {
    case effClose:
        plugin_destroy(p);
        return 1;
    case effEditGetRect:
        if (ptr)
            *(ERect **)ptr = &p->rect;
        return 1;
    case effEditOpen:
        return editor_open(p, (HWND)ptr);
    case effEditClose:
        editor_close(p);
        return 1;
    case effGetProgramName:
        if (ptr)
            copy_string(ptr, "Default", 24);
        return 1;
    case effGetEffectName:
    case effGetProductString:
        if (ptr)
            copy_string(ptr, PLUGIN_NAME, 32);
        return 1;
    case effGetVendorString:
        if (ptr)
            copy_string(ptr, PLUGIN_VENDOR, 32);
        return 1;
    case effGetVendorVersion:
        return PLUGIN_VERSION;
    case effGetVstVersion:
        return 2400;
    case effGetPlugCategory:
        return kPlugCategEffect;
    case effCanDo:
        return 0;
    }
    return 0;
}

static void process_replacing(AEffect *effect, float **inputs, float **outputs, int32_t frames)
{
    for (int ch = 0; ch < effect->numOutputs; ch++) {
        if (inputs[ch] != outputs[ch])
            memmove(outputs[ch], inputs[ch], (size_t)frames * sizeof(float));
    }
}

static void process_accumulating(AEffect *effect, float **inputs, float **outputs,
                                 int32_t frames)
{
    for (int ch = 0; ch < effect->numOutputs; ch++)
        for (int32_t i = 0; i < frames; i++)
            outputs[ch][i] += inputs[ch][i];
}

static void set_parameter(AEffect *effect, int32_t index, float value)
{
    (void)effect;
    (void)index;
    (void)value;
}

static float get_parameter(AEffect *effect, int32_t index)
{
    (void)effect;
    (void)index;
    return 0.0f;
}

/* Exported as both "VSTPluginMain" and the legacy "main" (see plugin.def). */
AEffect *VSTPluginMain(audioMasterCallback host)
{
    if (!host || host(NULL, audioMasterVersion, 0, 0, NULL, 0.0f) == 0)
        return NULL;

    Plugin *p = (Plugin *)calloc(1, sizeof(Plugin));
    if (!p)
        return NULL;
    p->host = host;
    p->rect.top = 0;
    p->rect.left = 0;
    p->rect.bottom = EDITOR_HEIGHT;
    p->rect.right = EDITOR_WIDTH;
    set_status(p, L"Starting YouTube Downloader...");

    AEffect *e = &p->effect;
    e->magic = VST_MAGIC;
    e->dispatcher = dispatcher;
    e->process = process_accumulating;
    e->processReplacing = process_replacing;
    e->setParameter = set_parameter;
    e->getParameter = get_parameter;
    e->numPrograms = 1;
    e->numParams = 0;
    e->numInputs = 2;
    e->numOutputs = 2;
    e->flags = effFlagsHasEditor | effFlagsCanReplacing | effFlagsNoSoundInStop;
    e->ioRatio = 1.0f;
    e->object = p;
    e->uniqueID = PLUGIN_UNIQUE_ID;
    e->version = PLUGIN_VERSION;
    return e;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        g_instance = instance;
        DisableThreadLibraryCalls(instance);
    } else if (reason == DLL_PROCESS_DETACH) {
        /* Unregister so a later reload at a different address doesn't reuse
         * a stale window procedure. */
        if (g_classes_registered) {
            UnregisterClassW(CONTAINER_CLASS, g_instance);
            UnregisterClassW(PARKING_CLASS, g_instance);
        }
    }
    return TRUE;
}
