"""Store provider secrets in macOS Keychain, never in settings or process arguments."""
import ctypes
import sys


def _security():
    if sys.platform != 'darwin':
        raise RuntimeError('API keys require macOS Keychain on this application.')
    lib = ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security')
    pointer = ctypes.c_void_p
    uint = ctypes.c_uint32
    lib.SecKeychainFindGenericPassword.argtypes = [pointer, uint, ctypes.c_char_p, uint, ctypes.c_char_p, ctypes.POINTER(uint), ctypes.POINTER(pointer), ctypes.POINTER(pointer)]
    lib.SecKeychainAddGenericPassword.argtypes = [pointer, uint, ctypes.c_char_p, uint, ctypes.c_char_p, uint, ctypes.c_char_p, ctypes.POINTER(pointer)]
    lib.SecKeychainItemModifyAttributesAndData.argtypes = [pointer, pointer, uint, ctypes.c_char_p]
    lib.SecKeychainItemFreeContent.argtypes = [pointer, pointer]
    lib.SecKeychainItemDelete.argtypes = [pointer]
    for name in ('SecKeychainFindGenericPassword', 'SecKeychainAddGenericPassword',
                 'SecKeychainItemModifyAttributesAndData', 'SecKeychainItemFreeContent',
                 'SecKeychainItemDelete'):
        getattr(lib, name).restype = ctypes.c_int32
    cf = ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
    cf.CFRelease.argtypes = [pointer]
    cf.CFRelease.restype = None
    return lib, cf


def _access(endpoint, key=None):
    lib, cf = _security()
    service = b'org.papers-to-kindle.provider'
    account = endpoint.rstrip('/').encode()
    length, data, item = ctypes.c_uint32(), ctypes.c_void_p(), ctypes.c_void_p()
    status = lib.SecKeychainFindGenericPassword(None, len(service), service, len(account), account, ctypes.byref(length), ctypes.byref(data), ctypes.byref(item))
    try:
        if status not in (0, -25300):
            raise RuntimeError('Keychain access failed. Unlock Keychain and retry.')
        if key is None:
            return ctypes.string_at(data, length.value).decode() if status == 0 else ''
        encoded = key.encode()
        if status == 0:
            status = lib.SecKeychainItemModifyAttributesAndData(item, None, len(encoded), encoded)
        else:
            status = lib.SecKeychainAddGenericPassword(None, len(service), service, len(account), account, len(encoded), encoded, None)
        if status:
            raise RuntimeError('Could not save the API key in Keychain.')
    finally:
        if data.value:
            lib.SecKeychainItemFreeContent(None, data)
        if item.value:
            cf.CFRelease(item)


def get_key(endpoint):
    return _access(endpoint)


def set_key(endpoint, key):
    _access(endpoint, key)
