# Security and privacy

RTL9210 Health Monitor temporarily takes privileged ownership of a USB storage
device. Treat transport and target-selection changes as storage-safety work.

## Private local data

First-time enrollment writes exact bridge, SSD, volume, and filesystem
identities to `config/device.plist`. Health captures under `runs/` contain raw
NVMe pages, including the SSD serial in `identify_controller.bin`. Both paths
are gitignored and must remain private.

The human-readable summary deliberately redacts the SSD serial. Do not attach a
raw run directory or local device profile to a public issue. Create a minimal,
manually reviewed excerpt instead.

Before publishing a fork, scan both tracked content and Git history for:

- hardware serials and volume UUIDs;
- volume labels, mount paths, hostnames, usernames and email addresses;
- raw controller pages and logs containing absolute paths;
- accidentally force-added files that match `.gitignore`.

## Reporting a vulnerability

Open a public issue only when the report contains no device identifiers or raw
storage evidence. For a disclosure that cannot be safely anonymized, use the
repository owner's private GitHub contact channel rather than posting the data.

## Scope

This project is not a recovery, repair, firmware, or destructive-diagnostics
tool. It implements only data-in identity and health commands. A clean SMART
reading does not guarantee that a drive will not fail; maintain independent,
tested backups.
