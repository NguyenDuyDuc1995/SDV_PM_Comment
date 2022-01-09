import os

# It means when use: <from _windows_application_icon_fix import *>, it will import all in <__all__> variable.
# If this module has many classes or functions, we need to add more code to import
__all__ = ['_taskbar_icon_fixed']

#  This program used for fixing an error when display icon on the task bar
if os.name == 'nt':
    import ctypes
    from ctypes import wintypes

    lpBuffer = wintypes.LPWSTR()
    AppUserModelID = ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID
    AppUserModelID(ctypes.cast(ctypes.byref(lpBuffer), wintypes.LPWSTR))
    appid = lpBuffer.value
    ctypes.windll.kernel32.LocalFree(lpBuffer)
    if not appid:
        appid = 'mica.hust.sdv_xray.1.0'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)


def _taskbar_icon_fixed():
    return True
