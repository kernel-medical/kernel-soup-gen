#!/usr/bin/env python3
"""
Validation test for kernel-soup-gen.
Creates a minimal fake kernel tree in a temp directory and verifies
that the tool extracts the expected fields correctly.
"""

import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "kernel-soup-gen.py"

DRIVER_CONTENT = textwrap.dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    // Copyright (C) 2025 Test Author <test@example.com>

    #include <linux/module.h>

    MODULE_DESCRIPTION("Test ADC driver for validation");
    MODULE_AUTHOR("Test Author <test@example.com>");
    MODULE_LICENSE("GPL-2.0-only");
""")

KCONFIG_CONTENT = textwrap.dedent("""\
    config TEST_ADC
        tristate "Test ADC driver"
        depends on SPI
        help
          Driver for test ADC.
""")

MAKEFILE_CONTENT = textwrap.dedent("""\
    VERSION = 6
    PATCHLEVEL = 15
    SUBLEVEL = 0
    NAME = Test Kernel
""")

MAINTAINERS_CONTENT = textwrap.dedent("""\
    TEST ADC DRIVER
    M:	Test Maintainer <maintainer@example.com>
    F:	drivers/iio/adc/test_adc.c
""")


def setup_kernel_tree(root: Path):
    """Create minimal fake kernel tree."""
    driver_dir = root / "drivers" / "iio" / "adc"
    driver_dir.mkdir(parents=True)
    (driver_dir / "test_adc.c").write_text(DRIVER_CONTENT)
    (driver_dir / "Kconfig").write_text(KCONFIG_CONTENT)

    (root / "Makefile").write_text(MAKEFILE_CONTENT)
    (root / "MAINTAINERS").write_text(MAINTAINERS_CONTENT)
    (root / "include" / "linux").mkdir(parents=True)

    # Initialise a git repo so git log commands don't fail
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "ci@test.local"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=root, check=True,
    )


def run_tool(kernel_root: Path, driver_rel: str, output_dir: Path) -> Path:
    driver_path = str(kernel_root / driver_rel)
    output_file = output_dir / "SOUP_test_adc.md"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), driver_path,
         "--kernel-root", str(kernel_root),
         "-o", str(output_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        raise RuntimeError(f"kernel-soup-gen exited with code {result.returncode}")
    return output_file


def check_output(output_file: Path):
    content = output_file.read_text()
    checks = [
        ("Module name",       "test_adc"),
        ("License",           "GPL-2.0-only"),
        ("Author",            "Test Author"),
        ("Kernel version",    "6.15"),
        ("Kconfig symbol",    "CONFIG_TEST_ADC"),
        ("TODO placeholder",  "complete this"),
    ]
    failures = []
    for label, expected in checks:
        if expected not in content:
            failures.append(f"  FAIL: {label!r} — expected {expected!r} not found in output")
        else:
            print(f"  PASS: {label}")
    return failures


def main():
    print(f"kernel-soup-gen validation — script: {SCRIPT}")
    if not SCRIPT.exists():
        print(f"ERROR: script not found at {SCRIPT}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        kernel_root = Path(tmpdir) / "linux"
        kernel_root.mkdir()
        output_dir = Path(tmpdir) / "output"
        output_dir.mkdir()

        print("Setting up fake kernel tree...")
        setup_kernel_tree(kernel_root)

        print("Running kernel-soup-gen...")
        output_file = run_tool(kernel_root, "drivers/iio/adc/test_adc.c", output_dir)

        print("Checking output fields:")
        failures = check_output(output_file)

    if failures:
        print("\nValidation FAILED:")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print("\nAll tests passed.")


if __name__ == "__main__":
    main()
