# RTL9210 NVMe SMART pass-through on macOS

## Executive summary

An NVMe SSD behind a Realtek RTL9210 USB bridge was fully usable as ordinary
APFS storage on macOS while Disk Utility and `diskutil` reported SMART as not
supported. smartmontools knew the Realtek `sntrealtek` command encoding, but its
Darwin build did not expose the SCSI transport needed to deliver that command
through the bridge.

The successful path uses Apple's `IOUSBHostDevice` API. The decisive step is to
capture the device, explicitly unconfigure it, and reconfigure it with interface
driver matching disabled. That prevents `IOUSBMassStorageUASDriver` from
immediately reclaiming interface 0. User space can then open the driverless
interface, select its Bulk-Only Transport alternate setting and issue the
read-only Realtek `0xE4` wrapper commands.

The method requires root for device capture but does not require a kernel
extension, SIP changes, firmware changes, Windows or a virtual machine.

The public repository excludes the original hardware serials, volume UUID,
filesystem labels, raw pages, local paths and Git identity. This memo preserves
technical method and negative evidence without publishing per-device evidence.

## Observed device topology

The validated bridge exposed one USB mass-storage interface with two alternate
settings:

| Alternate setting | Protocol | Role |
|---:|---:|---|
| 0 | `0x50` | USB Mass Storage Bulk-Only Transport (BOT) |
| 1 | `0x62` | USB Attached SCSI (UAS) |

macOS selected UAS and attached `IOUSBMassStorageUASDriver`. Ordinary block I/O,
APFS encryption and backup operation worked. The hidden NVMe controller's
health pages did not travel through the normal Disk Utility path.

The validated USB family identity was Realtek VID:PID `0bda:9210`. Device
revision, bridge serial, SSD identity and volume identity are intentionally
withheld and must be learned locally by guarded enrollment.

## Why existing approaches stopped short

### Native smartmontools

smartmontools implements `-d sntrealtek` for an NVMe device behind a Realtek
USB-to-NVMe bridge. The implementation supplies the vendor-specific command
wrapper; it still requires the operating system to provide a suitable SCSI
pass-through transport. The smartctl manual source places this device type in a
non-Darwin conditional block.

Result: the command encoding existed, but the installed macOS build could not
send it over this storage path.

### Apple SCSITask interfaces

The exact Realtek logical unit was located in IOKit. Registry-based creation of
the generic SCSI task plug-in was unavailable. Direct loading of Apple's signed
plug-in succeeded as a bundle operation, but probing the live logical unit
returned `kIOReturnNoDevice`; starting it returned
`kIOReturnUnsupported`. No SCSI command was sent.

Result: the generic user-space SCSI plug-in would not attach to the device while
the normal storage stack owned it.

### Ordinary IOUSBHost device capture

`IOUSBHostObjectInitOptionsDeviceCapture` terminated device clients, but the
UAS interface driver attached again. Attempts to open the interface returned
`kIOReturnNoResources` (`0xe00002be`).

Result: device-level capture did not by itself leave interface 0 driverless.

### QEMU and an ARM64 Linux guest

A privileged QEMU process could discover and expose the bridge descriptors to a
RAM-only Linux guest. The guest stalled while setting USB configuration 1 and
never created a block device. Forcing USB 2 was invalid because the bridge's
SuperSpeed bulk endpoint advertised a packet size incompatible with USB 2 bulk
transport.

Result: Linux smartmontools never acquired a device on which it could send
`sntrealtek`.

### SATA SMART extensions and firmware utilities

SAT SMART extensions target ATA commands behind a SCSI-to-ATA translation
layer. They do not implement the Realtek NVMe wrapper used here. RTL9210
firmware utilities configure or flash the bridge and are unrelated to a
read-only health query.

Result: wrong protocol in the first case and disproportionate destructive risk
in the second.

## Working macOS transport

The native probe performs this sequence:

1. Match exactly one enrolled `IOUSBHostDevice` by VID, PID, device revision
   and bridge serial. Enrollment mode accepts exactly one `0bda:9210` device and
   records the missing identity privately.
2. Open it with `IOUSBHostObjectInitOptionsDeviceCapture`.
3. Call `configureWithValue:0 matchInterfaces:NO`. Configuration zero
   unconfigures the USB device and tears down its interface objects, including
   the UAS driver's attachment point.
4. Call `configureWithValue:1 matchInterfaces:NO`. Configuration one recreates
   the interfaces without registering them for normal driver matching.
5. Wait for the device to become quiet and open its now-driverless
   `IOUSBHostInterface`.
6. Select alternate setting 0, the BOT path.
7. Open bulk IN endpoint `0x81` and bulk OUT endpoint `0x02`.
8. Send a 31-byte BOT Command Block Wrapper, receive the exact data-in length,
   and validate the 13-byte Command Status Wrapper.
9. Destroy the interface and device capture on every exit path, allowing macOS
   drivers to register again.

The shell front door separately proves the selected physical disk, its mounted
APFS volume and Time Machine idleness before the native capture. It cleanly
unmounts the whole disk, traps interruption and failure for remount, then proves
that the enrolled volume returned from the expected physical store.

## Realtek command wrapper

The transport uses a 16-byte vendor CDB whose first bytes are:

| Byte | Meaning |
|---:|---|
| 0 | Realtek vendor opcode `0xE4` |
| 1–2 | little-endian transfer length |
| 3 | NVMe opcode |
| 4 | low byte of command dword 10 |

Only these commands are present:

| Operation | NVMe opcode | CDW10 low byte | Length |
|---|---:|---:|---:|
| Identify Controller, CNS 1 | `0x06` | `0x01` | 4096 bytes |
| Get SMART/Health Log page | `0x02` | `0x02` | 512 bytes |
| Get Error Information Log page | `0x02` | `0x01` | 512 bytes |

The bridge-facing SCSI INQUIRY (`0x12`) is also read. Every BOT transaction is
data-in. Success requires:

- the complete 31-byte command wrapper transfer;
- the exact requested data length;
- a 13-byte status wrapper;
- status-wrapper signature `0x53425355`;
- the original command tag;
- status zero;
- residue zero.

There is no implementation of a storage write, firmware, format, sanitize,
self-test or namespace-management command.

## Enrollment and privacy boundary

The public code cannot safely pin a device using somebody else's identifiers.
`./rtl9210-health setup` therefore performs an explicit local enrollment:

1. The operator selects an external whole USB disk whose media name contains
   `RTL9210`.
2. The operator supplies a mounted APFS volume path.
3. The front door proves that the APFS physical store belongs to the selected
   disk.
4. Exactly one public-family `0bda:9210` bridge must be present.
5. After typed confirmation, the read-only capture obtains the bridge revision
   and serial plus the NVMe model and serial.
6. These values are stored in a mode-600, gitignored local plist.
7. All future probes require exact matches in both the shell and native layers.

The enrollment run contains a raw Identify Controller page and a private plist.
Both are intentionally ignored. The human summary suppresses the SSD serial,
but users must still treat firmware and lifetime counters as potentially
fingerprinting evidence.

The public Git repository must never contain:

- a real `config/device.plist`;
- raw controller pages or run directories;
- hardware serials or volume UUIDs;
- volume labels, absolute user paths, hostnames or personal email addresses;
- historical Git objects that previously contained any of the above.

## Remaining limitations

- Validation covers one Apple-silicon/macOS/RTL9210 configuration. Related
  Realtek variants may behave differently.
- Enrollment currently requires the bridge-facing media name to contain
  `RTL9210`, one mounted APFS volume and exactly one `0bda:9210` bridge.
- The endpoint addresses and alternate-setting layout are explicit. A firmware
  or device variant with another layout should fail rather than be guessed.
- USB capture resets the storage device. Cleanup substantially limits the
  operational risk but cannot remove hardware, firmware, power or filesystem
  risk.
- SMART is not a prediction guarantee. Maintain tested, independent backups.

## References

- [smartmontools source](https://github.com/smartmontools/smartmontools)
- [smartctl device-type manual source](https://github.com/smartmontools/smartmontools/blob/main/src/smartctl.8.in#L3121-L3163)
- [Apple `IOUSBHostDevice` configuration API](https://developer.apple.com/documentation/iousbhost/iousbhostdevice/configurewithvalue%3Amatchinterfaces%3Aerror%3A)
- [NVM Express health and error reporting overview](https://nvmexpress.org/how-ssds-fail-nvme-ssd-management-error-reporting-and-logging-capabilities/)
