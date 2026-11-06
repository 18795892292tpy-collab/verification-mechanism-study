"""Run commands one after another while asking Windows not to idle-sleep.

Usage: python harness/keep_awake.py -- <command 1> ;; <command 2> ...
The request (SetThreadExecutionState with ES_SYSTEM_REQUIRED) is held only while this process
runs and is released when it exits; no power setting is changed. A closed lid still sleeps.
"""
import ctypes
import subprocess
import sys

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--":
        args = args[1:]
    commands, cur = [], []
    for a in args:
        if a == ";;":
            commands.append(cur)
            cur = []
        else:
            cur.append(a)
    if cur:
        commands.append(cur)
    kernel = ctypes.windll.kernel32
    kernel.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    rc = 0
    try:
        for cmd in commands:
            print("running:", " ".join(cmd), flush=True)
            rc = subprocess.call(cmd) or rc
    finally:
        kernel.SetThreadExecutionState(ES_CONTINUOUS)
    return rc


if __name__ == "__main__":
    sys.exit(main())
