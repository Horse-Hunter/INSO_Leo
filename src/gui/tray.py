"""Windows notification icon; callbacks only publish commands to the Tk queue."""
import ctypes
import os
import threading
from ctypes import wintypes
from uuid import uuid4

from src.core.app_paths import application_name


class WindowsTray:
    def __init__(self, emit):
        self.emit = emit
        self.ready = threading.Event()
        self.thread = None
        self.hwnd = None
        self.user = None
        self.available = False
        self.stopping = threading.Event()

    def start(self):
        if os.name != 'nt' or self.stopping.is_set():
            return False
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name='notification-icon', daemon=True)
            self.thread.start()
        self.ready.wait(3)
        return self.available

    def stop(self):
        self.stopping.set()
        if self.hwnd and self.user:
            self.user.PostMessageW(self.hwnd, 0x0010, 0, 0)
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=3)

    def _run(self):
        user = ctypes.WinDLL('user32', use_last_error=True)
        shell = ctypes.WinDLL('shell32', use_last_error=True)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                                      wintypes.WPARAM, wintypes.LPARAM)

        class WindowClass(ctypes.Structure):
            _fields_ = [('style', wintypes.UINT), ('proc', proc_type),
                ('class_extra', ctypes.c_int), ('window_extra', ctypes.c_int),
                ('instance', wintypes.HINSTANCE), ('icon', wintypes.HICON),
                ('cursor', wintypes.HANDLE), ('background', wintypes.HBRUSH),
                ('menu', wintypes.LPCWSTR), ('name', wintypes.LPCWSTR)]

        class IconData(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('window', wintypes.HWND),
                ('identifier', wintypes.UINT), ('flags', wintypes.UINT),
                ('callback', wintypes.UINT), ('icon', wintypes.HICON),
                ('tip', wintypes.WCHAR * 128), ('state', wintypes.DWORD),
                ('state_mask', wintypes.DWORD), ('info', wintypes.WCHAR * 256),
                ('version', wintypes.UINT), ('info_title', wintypes.WCHAR * 64),
                ('info_flags', wintypes.DWORD), ('guid', ctypes.c_ubyte * 16),
                ('balloon_icon', wintypes.HICON)]

        user.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.DefWindowProcW.restype = ctypes.c_ssize_t
        user.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
            wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
        user.CreateWindowExW.restype = wintypes.HWND
        user.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        user.RegisterClassW.restype = wintypes.ATOM
        user.UnregisterClassW.argtypes = [wintypes.LPCWSTR, wintypes.HINSTANCE]
        user.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        user.LoadIconW.restype = wintypes.HICON
        user.CreatePopupMenu.restype = wintypes.HMENU
        user.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
        user.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p]
        user.TrackPopupMenu.restype = wintypes.UINT
        user.DestroyMenu.argtypes = [wintypes.HMENU]
        user.SetForegroundWindow.argtypes = [wintypes.HWND]
        user.DestroyWindow.argtypes = [wintypes.HWND]
        user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
        user.GetMessageW.restype = ctypes.c_int
        user.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user.DispatchMessageW.restype = ctypes.c_ssize_t
        shell.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(IconData)]
        shell.Shell_NotifyIconW.restype = wintypes.BOOL
        kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel.GetModuleHandleW.restype = wintypes.HMODULE
        icon = IconData()
        added = False
        taskbar_created = user.RegisterWindowMessageW('TaskbarCreated')

        def menu(hwnd):
            popup = user.CreatePopupMenu()
            if not popup:
                return
            try:
                user.AppendMenuW(popup, 0, 1, '打开 ' + application_name())
                user.AppendMenuW(popup, 0, 2, '退出')
                point = wintypes.POINT()
                user.GetCursorPos(ctypes.byref(point))
                user.SetForegroundWindow(hwnd)
                command = user.TrackPopupMenu(popup, 0x0100 | 0x0002, point.x, point.y, 0, hwnd, None)
                if command in {1, 2}:
                    self.emit('show' if command == 1 else 'exit')
                user.PostMessageW(hwnd, 0, 0, 0)
            finally:
                user.DestroyMenu(popup)

        @proc_type
        def procedure(hwnd, message, wparam, lparam):
            nonlocal added
            try:
                if message == 0x8001:
                    event = lparam & 0xffff
                    if event == 0x0203:
                        self.emit('show')
                    elif event in {0x0205, 0x007b}:
                        menu(hwnd)
                    return 0
                if message == taskbar_created and added:
                    shell.Shell_NotifyIconW(0, ctypes.byref(icon))
                    return 0
                if message == 0x0010:
                    user.DestroyWindow(hwnd)
                    return 0
                if message == 0x0002:
                    if added:
                        shell.Shell_NotifyIconW(2, ctypes.byref(icon))
                        added = False
                    self.hwnd = None
                    user.PostQuitMessage(0)
                    return 0
            except Exception:  # noqa: BLE001 - never unwind through a native callback
                return 0
            return user.DefWindowProcW(hwnd, message, wparam, lparam)

        name = 'INSOTray_' + uuid4().hex
        instance = kernel.GetModuleHandleW(None)
        window_class = WindowClass(proc=procedure, instance=instance, name=name)
        registered = False
        try:
            registered = bool(user.RegisterClassW(ctypes.byref(window_class)))
            if not registered:
                return
            hwnd = user.CreateWindowExW(0, name, application_name() + ' tray', 0, 0, 0, 0, 0,
                                        None, None, instance, None)
            if not hwnd:
                return
            self.hwnd, self.user = hwnd, user
            if self.stopping.is_set():
                user.DestroyWindow(hwnd)
                return
            icon.size, icon.window, icon.identifier = ctypes.sizeof(icon), hwnd, 1
            icon.flags, icon.callback = 1 | 2 | 4, 0x8001
            icon.icon, icon.tip = user.LoadIconW(None, ctypes.c_void_p(32512)), application_name()
            added = bool(shell.Shell_NotifyIconW(0, ctypes.byref(icon)))
            self.available = added
            self.ready.set()
            if not added or self.stopping.is_set():
                user.DestroyWindow(hwnd)
                return
            message = wintypes.MSG()
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                user.TranslateMessage(ctypes.byref(message))
                user.DispatchMessageW(ctypes.byref(message))
        finally:
            if added:
                shell.Shell_NotifyIconW(2, ctypes.byref(icon))
                added = False
            if self.hwnd:
                user.DestroyWindow(self.hwnd)
            self.available = False
            self.hwnd = None
            self.ready.set()
            if registered:
                user.UnregisterClassW(name, instance)
