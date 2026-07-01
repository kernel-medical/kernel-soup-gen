# Changelog

All notable changes to kernel-soup-gen are documented in this file.

## [1.0.0] — 2026-07-01

### Initial release

First public release of kernel-soup-gen — a command-line tool that
auto-generates IEC 62304 §8 SOUP records for Linux kernel drivers
directly from the kernel source tree.

#### Features

- Extracts `MODULE_AUTHOR`, `MODULE_DESCRIPTION`, `MODULE_LICENSE`
  from driver source via regex — no kernel build required
- Reads SPDX identifiers and copyright comment blocks for copyright
  holder list
- Detects kernel version from top-level `Makefile` (`VERSION`,
  `PATCHLEVEL`, `SUBLEVEL`)
- Calls `scripts/get_maintainer.pl` to identify official maintainers
  for traceability
- Walks directory tree upward to find Kconfig file and resolve
  `CONFIG_` symbol for the driver (tries exact stem, stripped
  suffixes `_MAIN _CORE _DRV _PCI _USB`, parent directory name)
- Queries `git log` for commit count, first/last commit date, and
  top three contributors by commit count
- Detects shallow clone (`.git/shallow`) and emits warning in both
  CLI output and generated document — instructs user to run
  `git fetch --unshallow` for complete history
- Generates CVE search link (NVD) and bugzilla search link per driver
- Outputs Markdown SOUP record with clearly marked `[TODO]`
  placeholders for fields requiring engineering judgment:
  - IEC 62304 safety class (A / B / C)
  - Purpose of SOUP item in the medical device
  - Known anomalies relevant to the device
  - Risk control measures (ISO 14971)

#### Output fields (per IEC 62304 §8.1.2)

| Field | Source | Auto/Manual |
|---|---|---|
| SOUP item name | MODULE_DESCRIPTION | Auto |
| SOUP item version | Kernel version + git SHA | Auto |
| Manufacturer | MODULE_AUTHOR | Auto |
| License | MODULE_LICENSE / SPDX | Auto |
| Maintainers | get_maintainer.pl | Auto |
| Kconfig symbol | Kconfig walk | Auto |
| Commit history | git log | Auto |
| CVE search | NVD link | Auto |
| Safety class | — | Manual [TODO] |
| Purpose in device | — | Manual [TODO] |
| Known anomalies | — | Manual [TODO] |
| Risk controls | — | Manual [TODO] |

#### Limitations

- Requires a local Linux kernel source tree with git history
- `scripts/get_maintainer.pl` must be executable (standard in kernel tree)
- Shallow clones produce incomplete commit history — tool warns
- Kconfig symbol detection may fail for drivers with non-standard
  file naming; tool falls back to `[UNKNOWN]` placeholder
- Does not assess functional suitability or risk — these require
  engineering judgment per IEC 62304 §8.1.2 c) and d)

#### Example

```
python3 kernel-soup-gen.py drivers/iio/adc/ti-ads1298.c
```

Output: `SOUP_ti-ads1298.md`

See `examples/SOUP_ti-ads1298.md` for a complete example record.

[1.0.0]: https://github.com/linux-medical-tools/kernel-soup-gen/releases/tag/v1.0.0
