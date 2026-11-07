"""Host A (native Windows) processor topology -> mask_A (PROTOCOL 3.7, 3.8).

Calls GetLogicalProcessorInformationEx(RelationProcessorCore) via ctypes and returns the lowest logical CPU of every
physical core (one thread per core). Deterministic, no randomness. Prints JSON; fails loudly off Windows or on an
unexpected record layout.
"""
import ctypes
import json
import sys

RELATION_PROCESSOR_CORE = 0
ERROR_INSUFFICIENT_BUFFER = 122


def physical_cores():
    """Return a list of cores; each core is a sorted list of logical CPU indices (processor group 0 only)."""
    if sys.platform != "win32":
        raise RuntimeError("topology_win.py runs on Windows only")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = k32.GetLogicalProcessorInformationEx
    fn.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    fn.restype = ctypes.c_int
    n = ctypes.c_ulong(0)
    fn(RELATION_PROCESSOR_CORE, None, ctypes.byref(n))
    if ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER or n.value == 0:
        raise RuntimeError("unexpected result sizing GetLogicalProcessorInformationEx")
    buf = ctypes.create_string_buffer(n.value)
    if not fn(RELATION_PROCESSOR_CORE, buf, ctypes.byref(n)):
        raise ctypes.WinError(ctypes.get_last_error())
    raw = buf.raw[: n.value]
    cores, off = [], 0
    while off < len(raw):
        rel = int.from_bytes(raw[off:off + 4], "little")
        size = int.from_bytes(raw[off + 4:off + 8], "little")
        if size == 0:
            raise RuntimeError("zero-size record in processor information")
        if rel == RELATION_PROCESSOR_CORE:
            # PROCESSOR_RELATIONSHIP at +8: Flags(1) EfficiencyClass(1) Reserved(20) GroupCount(2) GroupMask[]
            group_count = int.from_bytes(raw[off + 30:off + 32], "little")
            if group_count != 1:
                raise RuntimeError(f"core spans {group_count} processor groups; not supported")
            mask = int.from_bytes(raw[off + 32:off + 40], "little")
            group = int.from_bytes(raw[off + 40:off + 42], "little")
            if group != 0:
                raise RuntimeError("processor group != 0; not supported")
            cores.append([i for i in range(64) if mask >> i & 1])
        off += size
    return sorted(cores)


def mask_a():
    cores = physical_cores()
    cpus = [c[0] for c in cores]
    return {
        "physical_cores": len(cores),
        "logical_cpus": sum(len(c) for c in cores),
        "cores": cores,
        "cpu_list": cpus,
        "mask_hex": hex(sum(1 << i for i in cpus)),
    }


if __name__ == "__main__":
    print(json.dumps(mask_a()))
