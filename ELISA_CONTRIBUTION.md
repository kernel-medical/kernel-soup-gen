# ELISA White Paper Contribution
## Section: Kernel Driver SOUP Documentation — Automated Extraction Approach

*Proposed contribution to the ELISA Medical Devices Working Group*
*SOUP in Linux-based Medical Devices White Paper*

---

## 1. Introduction

IEC 62304 §8.1.2 requires that SOUP items be identified and documented
with specific traceability information. When a medical device runs
Linux, the number of SOUP items is large — a typical embedded Linux
image enables hundreds of kernel drivers, each of which is a distinct
SOUP item under IEC 62304.

Manual documentation of these items is error-prone and becomes
immediately outdated when the kernel version changes. This section
describes an automated approach to kernel driver SOUP documentation
that extracts the IEC 62304 §8.1.2 required fields directly from the
Linux kernel source tree.

---

## 2. IEC 62304 §8.1.2 Requirements for SOUP Items

IEC 62304 §8.1.2 requires the following to be documented for each
SOUP item:

| §8.1.2 Requirement | Description |
|---|---|
| a) Title, manufacturer, unique identifier | Name, author, version |
| b) Documented requirements for the SOUP item | Functional, performance, interface requirements |
| c) Hardware and software requirements | Platform constraints |
| d) Known anomalies | Bugs relevant to the safety context |

For Linux kernel drivers specifically, these map as follows:

| IEC 62304 §8.1.2 | Linux kernel source | Automated extraction |
|---|---|---|
| Title | `MODULE_DESCRIPTION()` macro | ✅ Regex extraction |
| Manufacturer / author | `MODULE_AUTHOR()` macro + SPDX | ✅ Regex extraction |
| Unique identifier | Kernel version + git commit SHA | ✅ `Makefile` + `git log` |
| License | `MODULE_LICENSE()` + SPDX header | ✅ Regex extraction |
| Maintainer (traceability) | `scripts/get_maintainer.pl` | ✅ Script call |
| Build dependency | `Kconfig` symbol (`CONFIG_*`) | ✅ Kconfig walk |
| Change history | `git log` statistics | ✅ Git query |
| Known anomalies (CVE) | NVD search link | ✅ Link generation |
| Purpose in device | Device-specific | ❌ Engineering judgment |
| Safety class | Context-specific | ❌ Engineering judgment |
| Risk controls | ISO 14971 FMEA | ❌ Engineering judgment |

The automated approach handles the traceable, objective fields. The
fields marked ❌ require engineering judgment and are left as clearly
marked placeholders in the output document.

---

## 3. Practical Considerations for Kernel Driver SOUP

### 3.1 Kernel version as SOUP version identifier

The Linux kernel version (`6.15.3` etc.) combined with the driver's
most recent commit SHA provides a precise unique identifier for a
SOUP item that satisfies IEC 62304 §8.1.2 a).

The kernel version is stable within a Long-Term Support (LTS) branch.
Medical device manufacturers should:
- Pin to an LTS kernel (currently: 6.1, 6.6, 6.12)
- Document the specific LTS kernel version and its EOL date
- Plan SOUP re-review at each kernel LTS version upgrade

### 3.2 Shallow clone warning

Many CI environments and developer workstations use shallow git clones
(`git clone --depth N`). A shallow clone truncates commit history,
which causes underreporting of:
- Total commit count
- First commit date (history of the SOUP item)
- Contributor list

Tools generating SOUP records from git history must detect and warn
about shallow clones. A full clone (`git fetch --unshallow`) is
required for accurate SOUP documentation.

### 3.3 Kconfig dependency tracking

IEC 62304 §8.1.2 requires documenting software and hardware
requirements for SOUP items. For Linux kernel drivers, the
`Kconfig` symbol (`CONFIG_TI_ADS1298`, `CONFIG_IGB`, etc.)
serves as the build-time dependency identifier.

The `CONFIG_` symbol:
- Uniquely identifies which version of the driver is compiled in
- Links to the complete Kconfig dependency chain
- Is the correct identifier to include in a software BOM (SBOM)

### 3.4 CVE monitoring for SOUP items

IEC 62304 §8.2.1 requires monitoring published anomalies for SOUP
items during maintenance. For Linux kernel drivers:

- The NVD (National Vulnerability Database) is the primary source
- Search query: `https://nvd.nist.gov/vuln/search/results?query=<driver-name>`
- The `MAINTAINERS` file and kernel security advisories
  (`https://www.kernel.org/doc/html/latest/process/security-bugs.html`)
  are additional sources

A SOUP management process for Linux must include periodic NVD review
for all enabled drivers in the device's kernel configuration.

---

## 4. Reference Implementation

The approach described in this section is implemented in
**kernel-soup-gen**, an open source tool:

```
https://github.com/linux-medical-tools/kernel-soup-gen
```

Usage:
```bash
python3 kernel-soup-gen.py drivers/iio/adc/ti-ads1298.c
```

The tool produces a Markdown SOUP record template with all
automatically extractable fields populated and engineering judgment
fields clearly marked as `[TODO]`.

A tool qualification document (IEC 62304 §6.1) is provided at:
```
https://github.com/linux-medical-tools/kernel-soup-gen/blob/main/TOOL_QUALIFICATION.md
```

---

## 5. Recommended SOUP Management Process for Linux Kernel Drivers

1. **Identify** — Run kernel-soup-gen for all drivers enabled in
   the device's `.config` to generate the initial SOUP inventory

2. **Evaluate** — Engineer completes [TODO] fields:
   - Assign IEC 62304 safety class based on device risk analysis
   - Document purpose of each driver in the device
   - Review NVD for known anomalies

3. **Control** — Pin to a specific LTS kernel version; document EOL
   date; schedule review at next LTS version

4. **Monitor** — Set up periodic NVD alerts for driver names;
   review kernel security advisories

5. **Update** — At each kernel LTS bump, re-run kernel-soup-gen
   and review diff against previous SOUP records; document changes

---

*Author: Md Shofiqul Islam*
*Upstream Linux kernel contributor — IIO subsystem*
*https://lore.kernel.org/all/?q=Md+Shofiqul+Islam*
*Contact: shofiqtest@gmail.com*
