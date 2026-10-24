#!/usr/bin/env python3
"""Reject redirected paths and external dependency storage before any capture."""
import os
import pathlib
import plistlib
import subprocess
import sys

if sys.version_info < (3, 9):
    raise SystemExit('Python 3.9+ required')
root = pathlib.Path(sys.argv[1]).resolve(strict=True)

def internal(path):
    data = subprocess.run(['/usr/sbin/diskutil', 'info', '-plist', str(path)],
                          check=True, capture_output=True, timeout=15)
    if plistlib.loads(data.stdout).get('Internal') is not True:
        raise SystemExit('Storage is not verified internal: ' + str(path))

internal(root)
for relative in ('.build', '.build/rtl9210_health_probe', 'runs', 'config',
                 'config/device.plist', 'scripts', 'scripts/volume_guard.py',
                 'scripts/bounded.py', 'scripts/privileged_worker.py', 'scripts/worker_client.py', 'scripts/storage_guard.py',
                 'scripts/macos-sudo-askpass', 'src', 'src/rtl9210_health_probe.m', 'src/cancellation.h'):
    target = root / relative
    for component in (target, *target.parents):
        if component == root:
            break
        if component.is_symlink():
            raise SystemExit('Refusing symlink: ' + str(component))
    existing = target
    while not existing.exists():
        existing = existing.parent
    internal(existing.resolve(strict=True))
# Executable, runtime prefixes and actual stdlib modules can differ with venvs.
for path in {sys.executable, sys.prefix, sys.base_prefix, os.__file__,
             subprocess.__file__, plistlib.__file__}:
    internal(pathlib.Path(path).resolve(strict=True))
