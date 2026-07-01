# Tool Qualification Document
## kernel-soup-gen v1.0.0

**Document ID:** KSG-TQ-001  
**Version:** 1.0.0  
**Date:** 2026-07-01  
**Author:** Md Shofiqul Islam  
**Status:** Released  

---

## 1. Purpose and Scope

This document provides tool qualification evidence for **kernel-soup-gen**
in accordance with IEC 62304:2015+AMD1:2015 §6.1 (Software Development
Tools).

kernel-soup-gen is a Python command-line tool that extracts metadata
from Linux kernel driver source files and generates IEC 62304 §8
SOUP (Software of Unknown Provenance) record templates.

This document covers:
- Tool classification per IEC 62304 §6.1
- Tool description and intended use
- Validation evidence
- Known limitations and residual risks

---

## 2. Regulatory Context

### 2.1 Applicable Standard

**IEC 62304:2015+AMD1:2015** — Medical device software — Software life
cycle processes

**§6.1 Software development tools:**
> "If a software development tool is used that can influence the
> development of software, the manufacturer shall document and maintain
> the requirements for each software tool used."

### 2.2 Tool Classification

Per IEC 62304 §6.1, tools are classified based on whether their output
could directly affect the safety of the medical device software.

| Question | Answer |
|---|---|
| Does the tool produce software that executes on the device? | **No** |
| Does the tool modify device software? | **No** |
| Does the tool produce documentation used in regulatory submission? | **Yes** |
| Could an error in the tool lead to incorrect SOUP records? | **Yes** |

**Classification: Class B tool** — tool output (SOUP records) is used
in regulatory submissions; an error could lead to incomplete SOUP
identification, which could result in unmitigated risk from the SOUP
item.

**Required qualification level:** Validation of tool output for the
intended use case.

---

## 3. Tool Description

### 3.1 Inputs

| Input | Description | Required |
|---|---|---|
| Kernel source file path | Relative path from kernel root (e.g. `drivers/iio/adc/ti-ads1298.c`) | Yes |
| Linux kernel source tree | Local checkout with `.git/` history | Yes |

### 3.2 Processing Steps

1. Locate kernel root by searching upward for `Makefile` containing `KERNELVERSION`
2. Extract `MODULE_AUTHOR`, `MODULE_DESCRIPTION`, `MODULE_LICENSE` via regex
3. Extract SPDX identifier from first line comment
4. Read kernel version from top-level `Makefile`
5. Call `scripts/get_maintainer.pl` for maintainer list
6. Walk directory tree upward to locate Kconfig file and resolve `CONFIG_` symbol
7. Query `git log` for commit statistics
8. Detect shallow clone via `.git/shallow`
9. Generate Markdown output with extracted fields and `[TODO]` placeholders

### 3.3 Outputs

A single Markdown file (`SOUP_<driver>.md`) containing:
- Automatically extracted fields (see CHANGELOG §Output fields)
- Clearly marked `[TODO]` placeholders for fields requiring
  engineering judgment

### 3.4 What the tool does NOT do

- Does not assess functional suitability of the SOUP item
- Does not determine IEC 62304 safety class
- Does not identify known anomalies relevant to the specific device
- Does not perform risk analysis
- Does not replace engineering review of the generated record

---

## 4. Validation Evidence

### 4.1 Validation approach

Tool validation was performed by comparing tool output against
manually extracted values for three representative kernel drivers
spanning different subsystems and file structures.

### 4.2 Test cases

#### Test Case 1: `drivers/iio/adc/ti-ads1298.c`

| Field | Expected | Tool output | Pass/Fail |
|---|---|---|---|
| Module name | `ti-ads1298` | `ti-ads1298` | ✅ Pass |
| Author | `Mike Looijmans <mike.looijmans@topic.nl>` | `Mike Looijmans <mike.looijmans@topic.nl>` | ✅ Pass |
| License | `GPL-2.0-only` | `GPL-2.0-only` | ✅ Pass |
| Kconfig symbol | `CONFIG_TI_ADS1298` | `CONFIG_TI_ADS1298` | ✅ Pass |
| Maintainer list | From get_maintainer.pl | Matches manual output | ✅ Pass |
| Commit count | Matches `git log --oneline` count | Verified | ✅ Pass |
| Shallow clone warning | Present when `.git/shallow` exists | Present | ✅ Pass |

#### Test Case 2: `drivers/net/ethernet/intel/igb/igb_main.c`

Tests non-standard naming (nested directory, `_main` suffix stripping):

| Field | Expected | Tool output | Pass/Fail |
|---|---|---|---|
| Kconfig symbol | `CONFIG_IGB` | `CONFIG_IGB` | ✅ Pass |
| Author extraction | Multiple authors | All extracted | ✅ Pass |

#### Test Case 3: `drivers/iio/accel/adxl372.c`

| Field | Expected | Tool output | Pass/Fail |
|---|---|---|---|
| Module name | `adxl372` | `adxl372` | ✅ Pass |
| License | `GPL-2.0+` | `GPL-2.0+` | ✅ Pass |
| Kconfig symbol | `CONFIG_ADXL372` | `CONFIG_ADXL372` | ✅ Pass |

### 4.3 Regression testing

A regression test script is provided in `tests/` that re-runs all
test cases and compares output to reference files using `diff`.

Run validation:
```bash
python3 tests/validate.py
```

Expected output: `All tests passed.`

---

## 5. Known Limitations and Residual Risks

| Limitation | Risk | Mitigation |
|---|---|---|
| Kconfig symbol not found for drivers with non-standard naming | SOUP record shows `[UNKNOWN]` for CONFIG symbol | User must manually identify symbol; tool marks it as `[TODO]` |
| Shallow git clone produces incomplete commit history | SOUP record underreports commit count and date range | Tool detects and warns; user must run `git fetch --unshallow` |
| MODULE_* macros not present in all drivers | Fields left as `[TODO]` | User must manually extract from source |
| get_maintainer.pl may return empty for unmaintained drivers | No maintainer listed | Tool marks as `[TODO: no maintainer found]` |
| Tool does not validate correctness of extracted data | Incorrect metadata if source has non-standard formatting | User must review all extracted fields before submission |

---

## 6. Conclusion

kernel-soup-gen v1.0.0 has been validated for the intended use case of
generating IEC 62304 §8 SOUP record templates from Linux kernel driver
source files.

**The tool is suitable for use as a documentation aid subject to the
following conditions:**

1. All `[TODO]` placeholders must be completed by a qualified engineer
2. All automatically extracted fields must be reviewed for correctness
3. The kernel source tree must be a full (non-shallow) clone
4. The generated SOUP record must be reviewed and approved as part of
   the manufacturer's IEC 62304 §8 SOUP management process

The tool does not replace engineering judgment. It reduces the manual
effort required to generate the boilerplate portions of a SOUP record.

---

## 7. Document Control

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-07-01 | Md Shofiqul Islam | Initial release |

---

*kernel-soup-gen is open source software licensed under MIT.*  
*Source: https://github.com/linux-medical-tools/kernel-soup-gen*  
*Tool qualification questions: shofiqtest@gmail.com*
