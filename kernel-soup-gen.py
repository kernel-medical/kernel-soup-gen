#!/usr/bin/env python3
"""
kernel-soup-gen: IEC 62304 §8 SOUP record generator for Linux kernel drivers.

Usage:
  kernel-soup-gen.py <driver-path> [--kernel-root <path>] [--output <file>]

Examples:
  kernel-soup-gen.py drivers/iio/adc/ti-ads1298.c
  kernel-soup-gen.py drivers/iio/health/max86150.c --kernel-root /path/to/linux
  kernel-soup-gen.py drivers/net/ethernet/intel/igb/igb_main.c -o igb_SOUP.md
"""

import argparse
import re
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip()


def find_kernel_root(start):
    """Walk up from start path to find Linux kernel root (has MAINTAINERS + Makefile)."""
    p = Path(start).resolve()
    candidates = [p] + list(p.parents)
    for candidate in candidates:
        if (candidate / "MAINTAINERS").exists() and (candidate / "Makefile").exists():
            if (candidate / "include" / "linux").exists():
                return candidate
    return None


def extract_module_macros(path):
    """Parse MODULE_AUTHOR, MODULE_DESCRIPTION, MODULE_LICENSE, SPDX from source."""
    try:
        content = Path(path).read_text(errors="replace")
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    info = {}
    for key, pattern in [
        ("author",      r'MODULE_AUTHOR\s*\(\s*"([^"]+)"'),
        ("description", r'MODULE_DESCRIPTION\s*\(\s*"([^"]+)"'),
        ("license",     r'MODULE_LICENSE\s*\(\s*"([^"]+)"'),
        ("spdx",        r'SPDX-License-Identifier:\s*(\S+)'),
    ]:
        m = re.search(pattern, content)
        if m:
            info[key] = m.group(1)

    info["aliases"] = re.findall(r'MODULE_ALIAS\s*\(\s*"([^"]+)"', content)
    info["copyrights"] = re.findall(r'(?:Copyright|copyright)\s.*', content)[:4]
    return info


def git_info(rel_path, kernel_root):
    """Extract commit history metadata for one driver file."""
    cwd = str(kernel_root)
    path = str(rel_path)

    # Detect shallow clone
    shallow = (Path(kernel_root) / ".git" / "shallow").exists()

    log = run(["git", "log", "--oneline", "--follow", "--", path], cwd=cwd)
    commits = [l for l in log.splitlines() if l.strip()]

    dates = run(
        ["git", "log", "--reverse", "--follow", "--format=%ad",
         "--date=short", "--", path], cwd=cwd
    )
    date_list = [d for d in dates.splitlines() if d.strip()]

    authors_raw = run(
        ["git", "log", "--follow", "--format=%aN", "--", path], cwd=cwd
    )
    author_counts = Counter(authors_raw.splitlines())

    return {
        "num_commits":    len(commits),
        "first_date":     date_list[0]  if date_list else "unknown",
        "last_date":      date_list[-1] if date_list else "unknown",
        "recent_commits": commits[:6],
        "top_authors":    author_counts.most_common(5),
        "shallow":        shallow,
    }


def kernel_version(kernel_root):
    """Read VERSION.PATCHLEVEL from top-level Makefile."""
    try:
        mk = (Path(kernel_root) / "Makefile").read_text()
        v = re.search(r"^VERSION\s*=\s*(\d+)", mk, re.M)
        p = re.search(r"^PATCHLEVEL\s*=\s*(\d+)", mk, re.M)
        s = re.search(r"^SUBLEVEL\s*=\s*(\d+)", mk, re.M)
        if v and p:
            ver = f"{v.group(1)}.{p.group(1)}"
            if s and s.group(1) != "0":
                ver += f".{s.group(1)}"
            return ver
    except Exception:
        pass
    tag = run(["git", "describe", "--tags", "--abbrev=0"], cwd=str(kernel_root))
    return tag or "unknown"


def maintainer_info(rel_path, kernel_root):
    """Run get_maintainer.pl and return top results."""
    script = Path(kernel_root) / "scripts" / "get_maintainer.pl"
    if not script.exists():
        return []
    out = run(["perl", str(script), "--nogit", str(rel_path)], cwd=str(kernel_root))
    return [l for l in out.splitlines() if l.strip()][:5]


def kconfig_deps(driver_abs, kernel_root):
    """Find the Kconfig entry for this driver, searching up the directory tree."""
    stem = driver_abs.stem.upper().replace("-", "_")
    # Build candidate symbols: exact stem, stem minus common suffixes, parent dir name
    suffixes = ["_MAIN", "_CORE", "_DRV", "_PCI", "_I2C", "_SPI", "_PLATFORM",
                "_BASE", "_HW", "_LIB", "_COMMON"]
    candidates = [stem]
    for suf in suffixes:
        if stem.endswith(suf):
            candidates.append(stem[: -len(suf)])
    candidates.append(driver_abs.parent.name.upper().replace("-", "_"))
    # Deduplicate while preserving order
    seen = set()
    symbols = [c for c in candidates if c not in seen and not seen.add(c)]

    search_dir = driver_abs.parent
    while search_dir != kernel_root.parent:
        kconfig = search_dir / "Kconfig"
        if kconfig.exists():
            content = kconfig.read_text(errors="replace")
            blocks = re.split(r"^config ", content, flags=re.M)
            for symbol in symbols:
                for block in blocks:
                    if block.split("\n")[0].strip() == symbol:
                        deps    = re.findall(r"^\s+depends on\s+(.+)$", block, re.M)
                        selects = re.findall(r"^\s+select\s+(.+)$",    block, re.M)
                        return deps, selects
        if search_dir == kernel_root:
            break
        search_dir = search_dir.parent
    return [], []


def generate(driver_path_arg, kernel_root_arg=None, output_arg=None):
    # Resolve paths
    if kernel_root_arg:
        kernel_root = Path(kernel_root_arg).resolve()
    else:
        kernel_root = find_kernel_root(driver_path_arg)
        if not kernel_root:
            # Maybe it is a relative path — try from cwd
            kernel_root = find_kernel_root(Path.cwd() / driver_path_arg)
        if not kernel_root:
            sys.exit("Error: cannot find kernel root. Use --kernel-root.")

    # Make absolute driver path
    driver_arg = Path(driver_path_arg)
    if driver_arg.is_absolute():
        abs_path = driver_arg.resolve()
    else:
        abs_path = (kernel_root / driver_arg).resolve()

    if not abs_path.exists():
        sys.exit(f"Error: driver not found: {abs_path}")

    rel_path = abs_path.relative_to(kernel_root)
    driver_name = abs_path.stem

    print(f"kernel-soup-gen: {rel_path}")
    print(f"  Kernel root : {kernel_root}")

    src   = extract_module_macros(abs_path)
    git   = git_info(rel_path, kernel_root)
    kver  = kernel_version(kernel_root)
    maint = maintainer_info(rel_path, kernel_root)
    deps, selects = kconfig_deps(abs_path, kernel_root)
    today = date.today().isoformat()

    print(f"  Kernel ver  : {kver}")
    if git["shallow"]:
        print("  WARNING: shallow clone — git history is incomplete. Run:")
        print("    git fetch --unshallow")
    print(f"  Commits     : {git['num_commits']}{' (incomplete — shallow clone)' if git['shallow'] else ''}")
    print(f"  Maintainers : {len(maint)} found")

    # ── Build the document ───────────────────────────────────────────────────
    L = []

    def h(text): L.append(f"## {text}\n")
    def row(k, v): L.append(f"| **{k}** | {v} |")
    def blank(): L.append("")

    L.append(f"# SOUP Record — `{driver_name}`")
    blank()
    L.append("**IEC 62304 §8 — Software of Unknown Provenance (SOUP)**")
    L.append(f"*Generated by [kernel-soup-gen](https://github.com/shofiqtest/kernel-soup-gen) on {today}*")
    blank()
    L.append("---")
    blank()

    h("Identification")
    L.append("| Field | Value |")
    L.append("|---|---|")
    row("SOUP Item",       f"`{driver_name}` — Linux kernel driver")
    row("Source file",     f"`{rel_path}`")
    row("Kernel version",  kver)
    row("License",         src.get("spdx", src.get("license", "see source")))
    if src.get("description"):
        row("Description", src["description"])
    if maint:
        row("Maintainer",  maint[0])
    row("First commit",    git["first_date"])
    row("Last commit",     git["last_date"])
    row("Total commits",   str(git["num_commits"]))
    row("Safety class",    "☐ Class A  ☐ Class B  ☐ Class C  *(complete this)*")
    row("Purpose in device", "*(complete this — what does this driver do in your product)*")
    blank()

    if src.get("copyrights"):
        h("Copyright")
        for c in src["copyrights"]:
            L.append(f"- {c.strip()}")
        blank()

    if deps or selects:
        h("Kconfig Dependencies")
        if deps:
            L.append(f"**depends on:** `{'`, `'.join(deps)}`")
        if selects:
            L.append(f"**selects:** `{'`, `'.join(selects)}`")
        blank()

    if maint:
        h("Maintainers")
        for m in maint:
            L.append(f"- {m}")
        blank()

    h("Git History")
    if git["shallow"]:
        L.append("> ⚠️ **Shallow clone detected** — history below is incomplete.")
        L.append("> Run `git fetch --unshallow` and regenerate for accurate contributor data.")
        blank()
    L.append("**Top contributors:**")
    blank()
    for author, count in git["top_authors"]:
        L.append(f"- {author} ({count} commit{'s' if count != 1 else ''})")
    blank()
    L.append("**Recent commits:**")
    blank()
    for c in git["recent_commits"]:
        L.append(f"- `{c}`")
    blank()

    h("Known Anomalies")
    L.append("> Search these sources and record findings below:")
    L.append(f"> - https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword={driver_name}")
    L.append(f"> - https://bugzilla.kernel.org/buglist.cgi?quicksearch={driver_name}")
    blank()
    L.append("| ID | Description | Severity | Mitigation |")
    L.append("|---|---|---|---|")
    L.append("| A-01 | No known CVEs at time of record creation | N/A | Monitor NVD for future disclosures |")
    L.append("| A-02 | *(add any known limitations or bugs here)* | — | — |")
    blank()

    h("Risk Classification (ISO 14971:2019)")
    L.append("| Hazard | Probability (1–5) | Severity (1–5) | Risk | Control |")
    L.append("|---|---|---|---|---|")
    L.append("| *(complete this for your specific device use case)* | | | | |")
    blank()

    h("Verification Requirements (IEC 62304 §8.1.3)")
    L.append(f"- [ ] Kernel version pinned to `{kver}` in build system")
    L.append("- [ ] Driver initialises correctly on target hardware")
    L.append("- [ ] Functional test on target hardware against device requirements")
    L.append("- [ ] No regressions on kernel LTS version upgrade")
    L.append("- [ ] Known anomalies reviewed and accepted or mitigated")
    blank()

    h("Change Control")
    L.append("| Date | Kernel version | Change | Author |")
    L.append("|---|---|---|---|")
    L.append(f"| {today} | {kver} | Initial SOUP record | *(your name)* |")
    blank()

    L.append("---")
    L.append("*Generated by [kernel-soup-gen](https://github.com/shofiqtest/kernel-soup-gen)*")

    output = "\n".join(L) + "\n"

    out_file = output_arg or f"SOUP_{driver_name}_{kver}.md"
    Path(out_file).write_text(output)
    print(f"  Output      : {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate IEC 62304 §8 SOUP records for Linux kernel drivers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("driver", help="Driver path (relative to kernel root or absolute)")
    parser.add_argument("--kernel-root", "-r", help="Path to kernel source root (auto-detected if omitted)")
    parser.add_argument("--output",      "-o", help="Output file path (default: SOUP_<driver>_<version>.md)")
    args = parser.parse_args()
    generate(args.driver, args.kernel_root, args.output)


if __name__ == "__main__":
    main()
