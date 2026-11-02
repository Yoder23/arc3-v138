"""Exact resource and input-stream guards extracted from the N44 frozen runtime."""
import ctypes,os,sys
def resource_limits(cpu_seconds=8, memory_bytes=1024**3):
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        return
    from ctypes import wintypes as w
    class BASIC(ctypes.Structure):
        _fields_ = [('ProcessTime', ctypes.c_longlong), ('JobTime', ctypes.c_longlong), ('Flags', w.DWORD), ('MinWS', ctypes.c_size_t), ('MaxWS', ctypes.c_size_t), ('Active', w.DWORD), ('Affinity', ctypes.c_size_t), ('Priority', w.DWORD), ('Scheduling', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ('ReadOps', 'WriteOps', 'OtherOps', 'ReadBytes', 'WriteBytes', 'OtherBytes')]
    class EXT(ctypes.Structure):
        _fields_ = [('Basic', BASIC), ('Io', IO), ('ProcessMemory', ctypes.c_size_t), ('JobMemory', ctypes.c_size_t), ('PeakProcess', ctypes.c_size_t), ('PeakJob', ctypes.c_size_t)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.restype = w.HANDLE
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.GetCurrentProcess.restype = w.HANDLE
    job = k.CreateJobObjectW(None, None)
    limits = EXT()
    limits.Basic.Flags = 0x2 | 0x8 | 0x100
    limits.Basic.ProcessTime = cpu_seconds * 10000000
    limits.Basic.Active = 1
    limits.ProcessMemory = memory_bytes
    if not job or not k.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(job, k.GetCurrentProcess()):
        raise RuntimeError('Required process resource guard unavailable: ' + str(ctypes.get_last_error()))
    return job


def deny_external_state(event, args):
    if event in ('open', 'os.listdir', 'os.scandir', 'subprocess.Popen', 'os.system', 'os.exec', 'os.fork', 'ctypes.dlopen', 'ctypes.dlsym') or event.startswith(('socket.', 'winreg.')):
        raise PermissionError('Programs cannot access external state')
