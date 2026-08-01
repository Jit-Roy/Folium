import ctypes
import os
import sys
from ctypes import wintypes

if sys.platform != "win32":
    raise RuntimeError("taskbar_icon_fix is Windows-only.")

import pythoncom
from win32com.propsys import propsys
from win32com.shell import shell, shellcon

# --------------------------------------------------------------------------
# Win32 constants (winuser.h) -- not all exposed by ctypes.wintypes
# --------------------------------------------------------------------------
GWL_EXSTYLE = -20
GCLP_HICON = -14
GCLP_HICONSM = -34

WS_EX_DLGMODALFRAME = 0x00000001

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020

WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1

user32 = ctypes.windll.user32

# 64-bit-safe signatures. Getting restype wrong here silently truncates
# pointer-sized values on 64-bit Python, which is the usual way these
# ctypes snippets go subtly wrong.
user32.GetWindowLongPtrW.restype = ctypes.c_void_p
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]

user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]

user32.SetClassLongPtrW.restype = ctypes.c_void_p
user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]

user32.SendMessageW.restype = ctypes.c_void_p
user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT,
]


# --------------------------------------------------------------------------
# FIX 3: title bar icon -- purely local, deterministic, no race
# --------------------------------------------------------------------------
_transparent_hicon = None

def hide_titlebar_icon(hwnd: int) -> None:
    """
    Forcefully inject a 16x16 transparent icon into the title bar (ICON_SMALL).
    We CANNOT use WS_EX_DLGMODALFRAME or pass 0 to WM_SETICON on Windows 11, 
    because Windows 11 DWM will automatically fall back to the taskbar's ICON_BIG 
    and shove it into the title bar!
    """
    global _transparent_hicon
    
    if _transparent_hicon is None:
        and_mask = (ctypes.c_byte * 32)()
        ctypes.memset(and_mask, 0xFF, 32)
        xor_mask = (ctypes.c_byte * 32)()
        ctypes.memset(xor_mask, 0x00, 32)
        _transparent_hicon = user32.CreateIcon(None, 16, 16, 1, 1, and_mask, xor_mask)

    # Forcefully push the transparent icon into the title bar
    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, _transparent_hicon)
    user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, _transparent_hicon)


# --------------------------------------------------------------------------
# FIX 1: taskbar icon -- synchronous, in-process, no external cache
# --------------------------------------------------------------------------
def apply_taskbar_identity(
    hwnd: int,
    aumid: str,
    icon_path: str,
    icon_index: int = 0,
    relaunch_command: str = None,
    display_name: str = None,
) -> None:
    """
    Set the taskbar identity (name/icon/relaunch command) directly on this
    window's property store, so Explorer never has to resolve anything
    against a shortcut on disk to know what to show for this HWND.

    icon_path: real filesystem path to a .ico file (not a Qt resource path).
    """
    if relaunch_command is None:
        relaunch_command = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    if display_name is None:
        display_name = aumid

    store = propsys.SHGetPropertyStoreForWindow(hwnd, propsys.IID_IPropertyStore)

    def set_str(canonical_name: str, value: str) -> None:
        try:
            key = propsys.PSGetPropertyKeyFromName(canonical_name)
        except AttributeError:
            # Fallback for older pywin32
            if canonical_name == "System.AppUserModel.ID":
                key = (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 5)
            elif canonical_name == "System.AppUserModel.RelaunchCommand":
                key = (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 2)
            elif canonical_name == "System.AppUserModel.RelaunchDisplayNameResource":
                key = (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 4)
            elif canonical_name == "System.AppUserModel.RelaunchIconResource":
                key = (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 3)
            else:
                raise
        
        store.SetValue(key, propsys.PROPVARIANTType(value, pythoncom.VT_LPWSTR))

    # Order matters: the docs are explicit that these go in before the
    # AppUserModel.ID property itself.
    set_str("System.AppUserModel.RelaunchCommand", relaunch_command)
    set_str("System.AppUserModel.RelaunchDisplayNameResource", display_name)
    set_str("System.AppUserModel.RelaunchIconResource", f"{icon_path},{icon_index}")
    set_str("System.AppUserModel.ID", aumid)  # this SetValue is what triggers
    #                                            the taskbar to refresh.
    store.Commit()


def clear_taskbar_identity(hwnd: int) -> None:
    """
    Best-effort cleanup. Microsoft's docs on SHGetPropertyStoreForWindow
    note that a window's properties should be cleared (VT_EMPTY) before
    the window closes, or the resources aren't released. Call from
    closeEvent.
    """
    try:
        store = propsys.SHGetPropertyStoreForWindow(hwnd, propsys.IID_IPropertyStore)
        empty = propsys.PROPVARIANTType(None, pythoncom.VT_EMPTY)
        
        def get_key(canonical_name):
            try:
                return propsys.PSGetPropertyKeyFromName(canonical_name)
            except AttributeError:
                if canonical_name == "System.AppUserModel.ID":
                    return (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 5)
                elif canonical_name == "System.AppUserModel.RelaunchCommand":
                    return (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 2)
                elif canonical_name == "System.AppUserModel.RelaunchDisplayNameResource":
                    return (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 4)
                elif canonical_name == "System.AppUserModel.RelaunchIconResource":
                    return (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 3)
                raise
                
        for name in (
            "System.AppUserModel.ID",
            "System.AppUserModel.RelaunchCommand",
            "System.AppUserModel.RelaunchDisplayNameResource",
            "System.AppUserModel.RelaunchIconResource",
        ):
            store.SetValue(get_key(name), empty)
        store.Commit()
    except Exception as exc:
        print(f"[taskbar_icon_fix] clear_taskbar_identity skipped: {exc}")


# --------------------------------------------------------------------------
# FIX 2: persistent registration -- not racy against *this* run at all
# --------------------------------------------------------------------------
def ensure_taskbar_shortcut(
    aumid: str,
    icon_path: str,
    icon_index: int = 0,
    target: str = None,
    arguments: str = None,
    shortcut_name: str = None,
) -> str:
    """
    Create (or overwrite) a per-user Start Menu shortcut carrying the same
    AppUserModelID, so Explorer has a durable answer independent of this
    process's runtime.
    """
    if target is None:
        target = sys.executable
    if arguments is None:
        arguments = f'"{os.path.abspath(sys.argv[0])}"'
    if shortcut_name is None:
        shortcut_name = aumid.split(".")[0] or "App"

    start_menu = os.path.join(
        os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"
    )
    os.makedirs(start_menu, exist_ok=True)
    shortcut_path = os.path.join(start_menu, f"{shortcut_name}.lnk")

    link = pythoncom.CoCreateInstance(
        shell.CLSID_ShellLink,
        None,
        pythoncom.CLSCTX_INPROC_SERVER,
        shell.IID_IShellLink,
    )
    link.SetPath(target)
    link.SetArguments(arguments)
    link.SetIconLocation(icon_path, icon_index)
    link.SetWorkingDirectory(os.path.dirname(os.path.abspath(sys.argv[0])))

    persist_file = link.QueryInterface(pythoncom.IID_IPersistFile)
    persist_file.Save(shortcut_path, 0)

    # Re-open the saved .lnk to stamp the AppUserModelID onto its own property store.
    store = propsys.SHGetPropertyStoreFromParsingName(
        shortcut_path, None, shellcon.GPS_READWRITE, propsys.IID_IPropertyStore
    )
    
    try:
        key = propsys.PSGetPropertyKeyFromName("System.AppUserModel.ID")
    except AttributeError:
        key = (pythoncom.MakeIID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 5)
        
    store.SetValue(
        key,
        propsys.PROPVARIANTType(aumid, pythoncom.VT_LPWSTR),
    )
    store.Commit()

    return shortcut_path


# --------------------------------------------------------------------------
# Convenience: one call, right before window.show()
# --------------------------------------------------------------------------
def setup_windows_identity(
    window,
    aumid: str,
    icon_path: str,
    icon_index: int = 0,
    display_name: str = None,
    create_start_menu_shortcut: bool = True,
) -> int:
    hwnd = int(window.winId())

    if create_start_menu_shortcut:
        try:
            ensure_taskbar_shortcut(aumid, icon_path, icon_index)
        except Exception as exc:
            print(f"[taskbar_icon_fix] shortcut registration skipped: {exc}")

    apply_taskbar_identity(
        hwnd, aumid, icon_path, icon_index, display_name=display_name
    )
    hide_titlebar_icon(hwnd)
    return hwnd
