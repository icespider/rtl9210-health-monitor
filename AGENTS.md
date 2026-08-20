# Agent instructions

Read `README.md` and `docs/rtl9210_macos_smart_passthrough.md` before changing
the transport or operator workflow.

## Non-negotiable safety controls

- Never invoke `.build/rtl9210_health_probe` directly. Use the front door.
- Never weaken exact device, physical-store, transfer-length, CSW, or remount
  validation to make unsupported hardware pass.
- Never add data-out, firmware, format, sanitize, self-test, or namespace
  commands to this read-only project.
- Never probe while Time Machine or another workload is active.
- Never commit `config/device.plist`, `runs/`, raw Identify Controller pages,
  hardware serials, volume UUIDs, mount labels, or absolute user paths.
- Enrollment must require an explicitly selected external whole USB disk, a
  verified mounted APFS physical store, exactly one RTL9210 bridge, and typed
  confirmation.
- Cleanup must attempt driver restoration and remount on normal exit, error,
  interruption, and transport failure.

## Verification

Run the smallest complete guard set after changes:

```bash
bash -n rtl9210-health
shellcheck rtl9210-health
xcrun clang -fobjc-arc -Wall -Wextra -Werror \
  -framework Foundation -framework IOKit -framework IOUSBHost \
  src/rtl9210_health_probe.m -o .build/rtl9210_health_probe
git diff --check
```

Do not perform a privileged device probe merely to test documentation or an
unrelated code path. A real probe temporarily resets a storage device and
requires an idle disk plus an informed local operator.
