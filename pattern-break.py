#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pattern-break.py
#
# Version 0.4.12
#
# -----------------------------------------------------------------------------
# A numeric gap detection tool for files & directories.
# -----------------------------------------------------------------------------
# Licensed under the GNU General Public License v3.0
#  (https://www.gnu.org/licenses/gpl-3.0.en.html)
#
# This script scans one or more directories (recursively if requested),
# gathers numeric coverage from filenames or directory names, and
# detects gaps ("missing" numeric IDs) in that coverage.
#
# Major Features:
#   - Multi-block numeric detection with various policies.
#   - Optionally detect ranges like 100-120 in filenames and expand coverage.
#   - Grouping by directory or cross-directory.
#   - Threshold-based splitting for large numeric jumps.
#   - Various output modes: summary, inline, csv, json, ascii-table, rich-table.
#   - Output destinations: stdout, file, or clipboard.
#
# Usage example:
#   pattern-break.py -d C:\myfiles --multi-range --format=rich-table --range=compact
#
# Windows note: Some table formats produce ANSI codes, which may require
#   - Windows 10+ with Virtual Terminal enabled (see enable_vt_mode() below), or
#   - The 'colorama' library to handle ANSI on older shells.
# -----------------------------------------------------------------------------

__version__ = "0.4.12"

import sys
import os
import re
import fnmatch
import argparse
import json
import time
import ctypes
from datetime import datetime

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

# Optional Rich usage (for an ANSI table).
try:
    from rich.console import Console
    from rich.table import Table
    from rich.box import ASCII
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

##############################################################################
# Optional: enable virtual terminal mode on Windows
##############################################################################
def enable_vt_mode():
    """
    Attempt to enable Windows 10+ Virtual Terminal Processing so that ANSI
    codes render correctly in cmd.exe or PowerShell.
    If we're not on Windows or the call fails, we ignore it gracefully.
    """
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11
            h_stdout = kernel32.GetStdHandle(-11)
            mode = ctypes.c_uint()
            # read current mode
            if kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode)) != 0:
                # 0x0004 is ENABLE_VIRTUAL_TERMINAL_PROCESSING
                mode.value |= 0x0004
                kernel32.SetConsoleMode(h_stdout, mode)
        except Exception:
            # If any error, just pass; color might not be enabled.
            pass

##############################################################################
# EXTENDED HELP TEXT
##############################################################################

EXTENDED_HELP = {
    "multi-range": r"""
If --multi-range is set, we parse '(\d+)-(\d+)' (by default) from the entire name,
merging that numeric range into coverage.
""",
    "range-regex": r"""
--range-regex <REGEX> (default='(\d+)-(\d+)')
Lets you override the default for multi-range expansions.
""",
    "block-policy": r"""
--block-policy [first|largest|all|multi-block-advanced]

 first   => only the first numeric block
 largest => only the largest numeric block
 all     => every numeric block => coverage set
 multi-block-advanced => the 7-step approach to treat each block distinctly,
                         never merging them incorrectly.
""",
    "ansi-issues": r"""
Windows CMD.exe with ANSI:
  If you're using an older Windows shell, ANSI sequences might not display
  properly. You can:
    - Use PowerShell or Windows Terminal with Virtual Terminal enabled.
    - Install 'colorama' to translate ANSI to Win32 calls.
    - Switch to ASCII-only table output: --format=ascii-table
    - Or use summary/inline/csv/json modes that don't rely on ANSI.
"""
}

def extended_help_lookup(argv):
    """Look for '-h topic' or '--help topic' to print extended help."""
    if "-h" in argv or "--help" in argv:
        idx = argv.index("-h") if "-h" in argv else argv.index("--help")
        if idx + 1 < len(argv):
            topic = argv[idx+1]
            if topic in EXTENDED_HELP:
                print(EXTENDED_HELP[topic])
                sys.exit(0)

##############################################################################
# ARGUMENT PARSING
##############################################################################

def parse_args():
    extended_help_lookup(sys.argv[1:])
    parser = argparse.ArgumentParser(
        description=f"pattern-break {__version__}: numeric gap detection tool.",
        add_help=False
    )
    parser.add_argument("--version","-V", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("--dir","-d", nargs="+", required=True,
                        help="Directories to scan.")
    parser.add_argument("--exclude","-xd", action="append",
                        help="Exclude pattern(s) (fnmatch). e.g. *.txt")
    parser.add_argument("--recursive","-r", action="store_true",
                        help="Recurse subdirectories (default=off).")

    parser.add_argument("--check", choices=["files","dirs","both"], default="files",
                        help="Analyze files, dirs, or both (default=files).")

    parser.add_argument("--pattern","-pt", help="Regex filter for names.")
    parser.add_argument("--filter","-ft", help="Substring filter for names.")
    parser.add_argument("--group-threshold","-gt", type=int,
                        help="Split groups if numeric gap > threshold.")
    parser.add_argument("--cross-dir-grouping", action="store_true",
                        help="Merge coverage from multiple dirs if numeric values align.")

    parser.add_argument("--block-policy", choices=["first","largest","all","multi-block-advanced"],
                        default="multi-block-advanced",
                        help="Which numeric blocks to interpret? (default=multi-block-advanced)")

    parser.add_argument("--multi-range", action="store_true",
                        help="Parse range-regex from entire name for expansions.")
    parser.add_argument("--range-regex", default=r"(\d+)-(\d+)",
                        help=r"Regex for multi-range coverage (default='(\d+)-(\d+)').")

    parser.add_argument("--start-num", type=int,
                        help="Force sequence start.")
    parser.add_argument("--end-num", type=int,
                        help="Force sequence end.")
    parser.add_argument("--mod-boundary", type=int,
                        help="If set, consider missing up to next boundary (e.g. mod=100).")
    parser.add_argument("--increment","-inc", type=int, default=1,
                        help="Step between consecutive numbers (default=1).")

    parser.add_argument("--format","-fmt",
                        choices=["inline","summary","csv","json","ascii-table","rich-table"],
                        default="summary",
                        help="How to present results. (default=summary).")
    parser.add_argument("--range", choices=["all","compact"], default="compact",
                        help="Show each missing item or just first..last in each segment.")
    parser.add_argument("--range-fmt", choices=["spacing","nospace"], default="nospace",
                        help="If 'spacing', blank lines between segments (summary/inline).")

    parser.add_argument("--show", choices=["filename","padded","number","significant"], default="filename",
                        help="How to display missing items (default=filename).")
    parser.add_argument("--explain", action="store_true",
                        help="Add reason text (leading, internal, etc).")
    parser.add_argument("--stats", action="store_true",
                        help="Show summary stats at the end.")
    parser.add_argument("--show-empty", action="store_true",
                        help="Include groups with 0 missing (default=off).")

    parser.add_argument("--verbose","-v", action="store_true",
                        help="Extra debug info (avg file size, etc).")
    parser.add_argument("--quiet","-q", action="store_true",
                        help="Suppress stdout (still can do file/clip).")

    parser.add_argument("--output","-o", action="append", choices=["stdout","file","clip","all"],
                        help="Where to send output (default=stdout).")
    parser.add_argument("--filename","-f",
                        help="If output includes 'file', specify filename.")

    parser.add_argument("-h","--help", action="help", default=argparse.SUPPRESS,
                        help="Show help or '-h topic' for extended topics like 'multi-range' or 'ansi-issues'.")
    return parser.parse_args()

##############################################################################
# COLLECTION LOGIC
##############################################################################

def collect_files(dirs, excludes, recursive):
    excludes = excludes or []
    out = {}
    def is_excluded(fp):
        bn = os.path.basename(fp)
        return any(fnmatch.fnmatch(bn,e) for e in excludes)

    for d in dirs:
        d_abs = os.path.abspath(d)
        if not os.path.isdir(d_abs):
            continue
        for root, subdirs, files in os.walk(d_abs):
            subdirs[:] = [sd for sd in subdirs if not is_excluded(os.path.join(root, sd))]
            if root not in out:
                out[root] = {"items": []}
            for f in files:
                fp = os.path.join(root, f)
                if not is_excluded(fp) and os.path.isfile(fp):
                    out[root]["items"].append({
                        "path": fp,
                        "name": f,
                        "size": os.path.getsize(fp),
                        "is_dir": False
                    })
            if not recursive:
                break
    return out

def collect_dirs(dirs, excludes, recursive):
    excludes = excludes or []
    out = {}
    def is_excluded(fp):
        bn = os.path.basename(fp)
        return any(fnmatch.fnmatch(bn,e) for e in excludes)

    for d in dirs:
        d_abs = os.path.abspath(d)
        if not os.path.isdir(d_abs):
            continue
        for root, subdirs, files in os.walk(d_abs):
            subdirs[:] = [sd for sd in subdirs if not is_excluded(os.path.join(root, sd))]
            if root not in out:
                out[root] = {"items": []}
            for sd in subdirs:
                sdp = os.path.join(root, sd)
                if not is_excluded(sdp):
                    out[root]["items"].append({
                        "path": sdp,
                        "name": sd,
                        "size": 0,
                        "is_dir": True
                    })
            if not recursive:
                break
    return out

def item_passes_filter(it, pat, subf):
    nm = it["name"]
    if pat and not re.search(pat, nm):
        return False
    if subf and (subf not in nm):
        return False
    return True

##############################################################################
# COVERAGE PARSING
##############################################################################

def parse_coverage_list(it, block_policy, multi_range, range_regex):
    """
    Given an item (file or directory) 'it' with name X,
    parse out all numeric blocks. Then apply:
      - block_policy to decide which blocks to interpret
      - multi_range to expand coverage if (\\d+)-(\\d+) is found
    Returns a list of coverage sets (each set is a list of integers).
    """
    nm = it["name"]
    blocks = re.findall(r"(\d+)", nm)
    if not blocks:
        return []

    blocks_i = [int(b) for b in blocks]

    def coverage_for_block(full_name, val):
        cov = set()
        cov.add(val)
        if multi_range:
            rngs = re.findall(range_regex, full_name)
            for m in rngs:
                if isinstance(m, (tuple, list)) and len(m) >= 2:
                    st = int(m[0])
                    ed = int(m[1])
                    lo = min(st, ed)
                    hi = max(st, ed)
                    for v in range(lo, hi+1):
                        cov.add(v)
        return sorted(cov)

    if block_policy == "first":
        v = blocks_i[0]
        c = coverage_for_block(nm, v)
        return [c] if c else []

    elif block_policy == "largest":
        v = max(blocks_i)
        c = coverage_for_block(nm, v)
        return [c] if c else []

    elif block_policy == "all":
        result = []
        for bval in blocks_i:
            c = coverage_for_block(nm, bval)
            if c:
                result.append(c)
        return result

    else:
        # multi-block-advanced => treat each block distinctly
        result = []
        for bval in blocks_i:
            c = coverage_for_block(nm, bval)
            if c:
                result.append(c)
        return result

##############################################################################
# GROUPING LOGIC
##############################################################################

def group_items(coll, args, artifact_type):
    cross_dir = args.cross_dir_grouping
    threshold = args.group_threshold

    if cross_dir:
        flat = []
        for dkey, stuff in coll.items():
            for it in stuff["items"]:
                if item_passes_filter(it, args.pattern, args.filter):
                    coverage_list = parse_coverage_list(it,
                                                        args.block_policy,
                                                        args.multi_range,
                                                        args.range_regex)
                    for cov in coverage_list:
                        flat.append((dkey, it, cov))
        return build_groups_from_flat(flat, threshold, artifact_type)
    else:
        out = []
        for dkey, stuff in coll.items():
            picks = []
            for it in stuff["items"]:
                if item_passes_filter(it, args.pattern, args.filter):
                    cov_list = parse_coverage_list(it,
                                                   args.block_policy,
                                                   args.multi_range,
                                                   args.range_regex)
                    for c in cov_list:
                        picks.append({"item": it, "coverage": c})
            if not picks:
                continue
            picks.sort(key=lambda x: (x["coverage"][0], x["item"]["name"]))
            out.extend(build_subgroups_in_dir(dkey, picks, threshold, artifact_type))
        return out

def build_subgroups_in_dir(dkey, picks, threshold, artifact_type):
    if not threshold:
        label = compute_group_label_for_picks(picks)
        return [{
            "group_id": f"{dkey}__group0",
            "directory": dkey,
            "label": label,
            "artifact_type": artifact_type,
            "picks": picks
        }]
    groups = []
    lastv = None
    citems = []
    idx = 0
    for p in picks:
        mv = p["coverage"][0]
        if lastv is None:
            citems = [p]
            lastv = mv
        else:
            if (mv - lastv) > threshold:
                lb = compute_group_label_for_picks(citems)
                groups.append({
                    "group_id": f"{dkey}__group{idx}",
                    "directory": dkey,
                    "label": lb,
                    "artifact_type": artifact_type,
                    "picks": citems
                })
                idx += 1
                citems = [p]
            else:
                citems.append(p)
            lastv = mv
    if citems:
        lb = compute_group_label_for_picks(citems)
        groups.append({
            "group_id": f"{dkey}__group{idx}",
            "directory": dkey,
            "label": lb,
            "artifact_type": artifact_type,
            "picks": citems
        })
    return groups

def build_groups_from_flat(flat, threshold, artifact_type):
    def min_cov(x):
        return x[2][0]
    flat.sort(key=lambda x: (min_cov(x), x[1]["name"]))
    groups = []
    citems = []
    idx = 0
    lastv = None
    for (dkey, it, cov) in flat:
        mv = cov[0]
        if lastv is None:
            citems = [(dkey, it, cov)]
            lastv = mv
        else:
            if threshold and (mv - lastv) > threshold:
                lb = compute_group_label_for_flat(citems)
                groups.append({
                    "group_id": f"crossdir_{idx}",
                    "directory": None,
                    "label": lb,
                    "artifact_type": artifact_type,
                    "picks": [{"item": xx[1], "coverage": xx[2]} for xx in citems]
                })
                idx += 1
                citems = [(dkey, it, cov)]
            else:
                citems.append((dkey, it, cov))
            lastv = mv
    if citems:
        lb = compute_group_label_for_flat(citems)
        groups.append({
            "group_id": f"crossdir_{idx}",
            "directory": None,
            "label": lb,
            "artifact_type": artifact_type,
            "picks": [{"item": xx[1], "coverage": xx[2]} for xx in citems]
        })
    return groups

def compute_group_label_for_picks(picks):
    for p in picks:
        coverage = p["coverage"]
        if coverage:
            val = coverage[0]
            nm = p["item"]["name"]
            zval = str(val).zfill(len(str(val)))
            idx = nm.find(zval)
            if idx < 0:
                idx = nm.find(str(val))
                if idx < 0:
                    return "<no-numeric>"
            prefix = nm[:idx]
            prefix = re.sub(r"\d+$", "", prefix)
            return prefix if prefix else "<no-numeric>"
    return "<no-numeric>"

def compute_group_label_for_flat(citems):
    for (dk, it, cov) in citems:
        if cov:
            val = cov[0]
            nm = it["name"]
            zval = str(val).zfill(len(str(val)))
            idx = nm.find(zval)
            if idx < 0:
                idx = nm.find(str(val))
                if idx < 0:
                    return "<no-numeric>"
            prefix = nm[:idx]
            prefix = re.sub(r"\d+$", "", prefix)
            return prefix if prefix else "<no-numeric>"
    return "<no-numeric>"

##############################################################################
# MISSING DETECTION
##############################################################################

def detect_breaks_in_group(group,
                           start_num=None,
                           end_num=None,
                           mod_boundary=None,
                           increment=1,
                           explain=False):
    picks = group["picks"]
    artifact_type = group["artifact_type"]
    if not picks:
        return {
            "group_info": group,
            "segments": [],
            "stats": {"num_missing": 0, "num_real": 0, "num_segments": 0, "approx_missing_bytes": 0}
        }

    all_ints = set()
    real_cov_items = []
    total_size = 0
    real_count = 0

    for p in picks:
        it = p["item"]
        coverage = p["coverage"]
        if artifact_type == "files":
            total_size += it["size"]
            real_count += 1
        main_val = coverage[0]
        px, sx = guess_prefix_suffix(it, main_val)
        for v in coverage:
            all_ints.add(v)
            real_cov_items.append({
                "val": v,
                "prefix": px,
                "suffix": sx,
                "is_dir": it["is_dir"],
                "size": it["size"]
            })

    sorted_ints = sorted(all_ints)
    if not sorted_ints:
        return {
            "group_info": group,
            "segments": [],
            "stats": {"num_missing": 0, "num_real": 0, "num_segments": 0, "approx_missing_bytes": 0}
        }

    actual_min = sorted_ints[0]
    actual_max = sorted_ints[-1]

    # Decide sequence start
    if start_num is not None:
        seq_start = start_num
    else:
        seq_start = actual_min
        if mod_boundary:
            seq_start = (seq_start // mod_boundary) * mod_boundary

    # Decide sequence end
    if end_num is not None:
        seq_end = end_num
    else:
        seq_end = actual_max
        if mod_boundary:
            seq_end = ((seq_end // mod_boundary) + 1) * mod_boundary - 1

    segments = []

    # Leading
    if seq_start < actual_min:
        st = seq_start
        ed = actual_min - increment
        seg = build_missing_segment(st, ed, "leading", explain, mod_boundary, increment)
        if seg["count"] > 0:
            segments.append(seg)

    # Internal
    for i in range(len(sorted_ints) - 1):
        cval = sorted_ints[i]
        nval = sorted_ints[i+1]
        if (nval - cval) > increment:
            st = cval + increment
            ed = nval - 1
            seg = build_missing_segment(st, ed, "internal", explain, mod_boundary, increment)
            if seg["count"] > 0:
                segments.append(seg)

    # Trailing
    if seq_end > actual_max:
        st = actual_max + increment
        ed = seq_end
        seg = build_missing_segment(st, ed, "trailing", explain, mod_boundary, increment)
        if seg["count"] > 0:
            segments.append(seg)

    total_missing = sum(s["count"] for s in segments)
    approx_bytes = 0
    if artifact_type == "files" and real_count > 0:
        avg_sz = total_size / real_count
        approx_bytes = avg_sz * total_missing

    # fill prefix
    for seg in segments:
        for mi in seg["missing_items"]:
            near = find_closest_prefix_suffix(mi["val"], real_cov_items)
            mi["prefix"] = near["prefix"]
            mi["suffix"] = near["suffix"]

    return {
        "group_info": group,
        "segments": segments,
        "stats": {
            "num_missing": total_missing,
            "num_real": real_count if artifact_type == "files" else len(sorted_ints),
            "num_segments": len(segments),
            "approx_missing_bytes": approx_bytes
        }
    }

def guess_prefix_suffix(it, example_val):
    nm = it["name"]
    zstr = str(example_val).zfill(len(str(example_val)))
    idx = nm.find(zstr)
    if idx < 0:
        idx2 = nm.find(str(example_val))
        if idx2 < 0:
            return ("???_", ".xxx")
        else:
            px = nm[:idx2]
            sx = nm[idx2+len(str(example_val)):]
            return (px, sx)
    else:
        px = nm[:idx]
        sx = nm[idx+len(zstr):]
        return (px, sx)

def build_missing_segment(st, ed, btype, explain, mod_boundary, inc):
    if ed < st:
        return {"start_val": st, "end_val": ed, "count": 0, "boundary_type": btype, "missing_items": []}
    items = []
    pad_len = len(str(ed))
    v = st
    while v <= ed:
        pstr = str(v).zfill(pad_len)
        reason = btype
        if explain and btype in ["leading","trailing"] and mod_boundary:
            reason += " (possible boundary)"
        items.append({
            "val": v,
            "padded": pstr,
            "prefix": "",
            "suffix": "",
            "reason": reason
        })
        v += inc
    return {
        "start_val": st,
        "end_val": ed,
        "count": len(items),
        "boundary_type": btype,
        "missing_items": items
    }

def find_closest_prefix_suffix(val, real_cov):
    best = None
    best_diff = float("inf")
    for rc in real_cov:
        diff = abs(rc["val"] - val)
        if diff < best_diff:
            best_diff = diff
            best = rc
    if best:
        return {"prefix": best["prefix"], "suffix": best["suffix"]}
    else:
        return {"prefix": "???_", "suffix": ".xxx"}

##############################################################################
# OUTPUT FORMATTING
##############################################################################

def format_results(all_groups, args):
    fmt = args.format
    if fmt == "csv":
        return format_csv(all_groups, args)
    elif fmt == "json":
        return format_json(all_groups, args)
    elif fmt == "inline":
        return format_inline(all_groups, args)
    elif fmt == "ascii-table":
        return format_ascii_table(all_groups, args)
    elif fmt == "rich-table":
        if HAS_RICH:
            return format_rich_table(all_groups, args)
        else:
            return "[Error] rich-table requested but 'rich' not installed."
    else:
        return format_summary(all_groups, args)

def reconstruct(mi, show_mode):
    if show_mode == "filename":
        return f"{mi['prefix']}{mi['padded']}{mi['suffix']}"
    elif show_mode == "padded":
        return mi["padded"]
    elif show_mode == "number":
        return str(mi["val"])
    elif show_mode == "significant":
        # e.g. last 3 digits
        return mi["padded"][-3:]
    else:
        return f"{mi['prefix']}{mi['padded']}{mi['suffix']}"

def global_stats_summary(bres, args):
    group_count = 0
    total_missing = 0
    total_real = 0
    total_segments = 0
    total_bytes = 0
    for br in bres:
        if not br["segments"] and not args.show_empty:
            continue
        group_count += 1
        st = br["stats"]
        total_missing += st["num_missing"]
        total_real += st["num_real"]
        total_segments += st["num_segments"]
        total_bytes += st["approx_missing_bytes"]
    approx_mb = total_bytes / (1024 * 1024)
    return f"STATS => groups:{group_count}, segments:{total_segments}, found:{total_real}, missing:{total_missing}, ~{approx_mb:.2f}MB missing"

##############################################################################
# Shared helper for table modes: build a textual segment representation
##############################################################################

def build_segment_text(segment, show_mode, range_mode, artifact_type, explain):
    """
    Returns a single string describing the missing items in one segment,
    respecting range_mode ('all' or 'compact'), show_mode, etc.
    Example (compact, 2 items):
      "dogs_m061061.jpg..dogs_m061062.jpg (2)"
    Example (all, 2 items):
      "dogs_m061061.jpg (internal); dogs_m061062.jpg (internal)"
    """
    c = segment["count"]
    if c == 0:
        return ""

    mis = segment["missing_items"]
    if range_mode == "all":
        # list each item
        parts = []
        for mi in mis:
            lbl = reconstruct(mi, show_mode)
            # optionally add reason
            reason_str = f" ({mi['reason']})" if explain else ""
            parts.append(f"{lbl}{reason_str}")
        return "; ".join(parts)
    else:
        # compact
        if c == 1:
            mi = mis[0]
            lbl = reconstruct(mi, show_mode)
            reason_str = f" ({mi['reason']})" if explain else ""
            # e.g. "dogs_m006057.jpg (1) (internal)"
            return f"{lbl} ({c}){reason_str}"
        else:
            fmi = mis[0]
            lmi = mis[-1]
            lbl1 = reconstruct(fmi, show_mode)
            lbl2 = reconstruct(lmi, show_mode)
            reason_str = f" ({fmi['reason']})" if explain else ""
            # e.g. "dogs_m061061.jpg..dogs_m061062.jpg (2)"
            return f"{lbl1}..{lbl2} ({c}){reason_str}"

##############################################################################
# Formatting: Inline, Summary, CSV, JSON
##############################################################################

def format_inline(bres, args):
    lines = []
    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue

        lines.append(f"Grp #{gcount}: {grp.get('label','')} (dir:{grp.get('directory')})")
        gcount += 1

        if not segs:
            lines.append("  No missing segments.")
            continue

        for i, s in enumerate(segs):
            if s["count"] == 0:
                continue
            if i > 0 and args.range_fmt == "spacing":
                lines.append("")
            # build text
            segtxt = build_segment_text(s, args.show, args.range, grp["artifact_type"], args.explain)
            # Indent
            for linepart in segtxt.split("; "):
                lines.append(f"  {linepart}")

        if args.verbose:
            st = br["stats"]
            approx_mb = st["approx_missing_bytes"]/(1024*1024)
            lines.append(f"  [dbg] found={st['num_real']} missing={st['num_missing']} ~{approx_mb:.2f}MB missing")

    if args.stats:
        lines.append("")
        lines.append(global_stats_summary(bres, args))

    return "\n".join(lines)

def format_summary(bres, args):
    lines = []
    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue

        lines.append(f"Grp #{gcount}: {grp.get('label','')} (dir:{grp.get('directory')}) {{")
        gcount += 1

        if not segs:
            lines.append("  No missing segments.")
            lines.append("}")
            continue

        for i, s in enumerate(segs):
            if s["count"] == 0:
                continue
            if i > 0 and args.range_fmt == "spacing":
                lines.append("")
            segtxt = build_segment_text(s, args.show, args.range, grp["artifact_type"], args.explain)
            for linepart in segtxt.split("; "):
                lines.append(f"  {linepart}")
        lines.append("}")
        if args.verbose:
            st = br["stats"]
            approx_mb = st["approx_missing_bytes"]/(1024*1024)
            lines.append(f"  [dbg] found={st['num_real']} missing={st['num_missing']} ~{approx_mb:.2f}MB missing")

    if args.stats:
        lines.append("")
        lines.append(global_stats_summary(bres, args))

    return "\n".join(lines)

def format_csv(bres, args):
    lines = []
    header = ["group_id","directory","artifact_type","missing_val","missing_label","reason"]
    lines.append(",".join(header))

    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue
        group_id = f"group_{gcount}"
        gcount += 1
        dir_ = grp.get("directory","")
        atype = grp.get("artifact_type","files")

        if not segs:
            continue

        for s in segs:
            if s["count"] == 0:
                continue
            if args.range == "all":
                for mi in s["missing_items"]:
                    lbl = reconstruct(mi, args.show)
                    reason = mi["reason"] if args.explain else ""
                    row = [group_id, dir_, atype, str(mi["val"]), lbl, reason]
                    lines.append(",".join(csv_escape(x) for x in row))
            else:
                # compact => first..last only
                c = s["count"]
                mis = s["missing_items"]
                if c == 1:
                    mi = mis[0]
                    lbl = reconstruct(mi, args.show)
                    reason = mi["reason"] if args.explain else ""
                    row = [group_id, dir_, atype, str(mi["val"]), lbl, reason]
                    lines.append(",".join(csv_escape(x) for x in row))
                else:
                    fmi = mis[0]
                    lmi = mis[-1]
                    lbl1 = reconstruct(fmi, args.show)
                    lbl2 = reconstruct(lmi, args.show)
                    reason = fmi["reason"] if args.explain else ""
                    rng_label = f"{lbl1}..{lbl2} ({c} {atype})"
                    row = [group_id, dir_, atype, f"{fmi['val']}..{lmi['val']}", rng_label, reason]
                    lines.append(",".join(csv_escape(x) for x in row))

    if args.stats:
        lines.append(f"# {global_stats_summary(bres,args)}")

    return "\n".join(lines)

def csv_escape(s):
    s = str(s).replace('"','""')
    if any(x in s for x in [',','"','\n','\r']):
        s = f'"{s}"'
    return s

def format_json(bres, args):
    data = []
    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue
        group_id = f"group_{gcount}"
        gcount += 1

        seg_data = []
        for s in segs:
            missing_data = []
            for mi in s["missing_items"]:
                lbl = reconstruct(mi, args.show)
                missing_data.append({
                    "val": mi["val"],
                    "label": lbl,
                    "reason": mi["reason"] if args.explain else ""
                })

            seg_data.append({
                "start_val": s["start_val"],
                "end_val": s["end_val"],
                "count": s["count"],
                "boundary_type": s["boundary_type"],
                "missing_items": missing_data
            })

        data.append({
            "group_id": group_id,
            "directory": grp.get("directory",""),
            "label": grp.get("label",""),
            "artifact_type": grp.get("artifact_type","files"),
            "segments": seg_data,
            "stats": br["stats"]
        })

    if args.stats:
        global_st = global_stats_summary(bres, args)
        return json.dumps({"results": data, "summary": global_st}, indent=2)
    else:
        return json.dumps({"results": data}, indent=2)

##############################################################################
# Formatting: ASCII Table / Rich Table
##############################################################################

def format_ascii_table(bres, args):
    """
    Produce a minimal ASCII table, but show missing items according to
    --show and --range. We create one row per segment. 
    If range=all, the cell may become large. If range=compact, we do
    first..last style or single item with reason if enabled.
    """
    lines = []
    divider = "+" + "-"*10 + "+" + "-"*60 + "+" + "-"*12 + "+"
    header  = "| Group ID | Missing Items / Segment                                     | Count       |"
    lines.append(divider)
    lines.append(header)
    lines.append(divider)

    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue
        group_id = f"G{gcount}"
        gcount += 1

        for s in segs:
            c = s["count"]
            if c == 0:
                continue
            # Build a textual description using build_segment_text
            segtxt = build_segment_text(s, args.show, args.range, grp["artifact_type"], args.explain)
            # We could break it up if it exceeds 60 chars, but let's just put it in one line.
            # We'll just store the entire string in the cell
            # Possibly format the count in a separate cell or reuse c in the text
            cell_count = str(c)
            # We'll keep it consistent with our header columns
            # We'll do a row with group_id, segtxt, c. 
            # But note that segtxt might already include the count in parentheses.
            # We'll still store c in the last column for quick scanning.

            # We can do a simple fixed width or left-justify with ljust, rjust, etc.
            # For safety, let's just store them as is, truncated if needed. 
            segtxt_disp = segtxt[:58] + "…" if len(segtxt) > 59 else segtxt

            row = f"| {group_id:<8} | {segtxt_disp:<59} | {cell_count:<10} |"
            lines.append(row)
        lines.append(divider)

    if args.stats:
        lines.append("")
        lines.append(global_stats_summary(bres, args))

    return "\n".join(lines)

def format_rich_table(bres, args):
    """
    Produce a Rich-based table with a column for Group #, Directory, Label,
    and Missing Items. The "Missing Items" uses the same segment-based logic
    but is joined with '; ' if multiple segments in a group.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold magenta", box=ASCII)
    table.add_column("Grp #", justify="center")
    table.add_column("Directory", justify="left")
    table.add_column("Label", justify="left")
    table.add_column("Missing Items / Segments", justify="left", max_width=80)

    gcount = 1
    for br in bres:
        segs = br["segments"]
        grp = br["group_info"]
        if not segs and not args.show_empty:
            continue
        group_id = str(gcount)
        gcount += 1

        # We'll build a single string that describes *all* missing segments in this group
        # or if you prefer, we can do one row per segment. But let's keep it simpler 
        # to match the summary approach.
        if not segs:
            # No missing => possibly add row or skip
            # We'll skip if show_empty is false, but we wouldn't be in here if not segs
            table.add_row(group_id, grp.get('directory',''), grp.get('label',''), "[No missing segments]")
            continue

        seg_parts = []
        for s in segs:
            if s["count"] == 0:
                continue
            segtxt = build_segment_text(s, args.show, args.range, grp["artifact_type"], args.explain)
            seg_parts.append(segtxt)

        missing_str = "; ".join(seg_parts) if seg_parts else "No missing"
        dir_ = grp.get("directory","")
        lbl = grp.get("label","")

        table.add_row(group_id, dir_, lbl, missing_str)

    # Capture the table output and append stats
    from io import StringIO
    buf = StringIO()
    with console.capture() as capture:
        console.print(table)
    table_str = capture.get()

    if args.stats:
        table_str += "\n" + global_stats_summary(bres, args)

    return table_str

##############################################################################
# MAIN
##############################################################################

def main():
    # Optional: enable vt mode for color in Windows 10+ cmd.exe
    enable_vt_mode()

    args = parse_args()

    # 1) gather
    file_groups = []
    dir_groups = []

    if args.check in ["files", "both"]:
        cf = collect_files(args.dir, args.exclude, args.recursive)
        gf = group_items(cf, args, "files")
        for i,g in enumerate(gf):
            br = detect_breaks_in_group(g,
                                        start_num=args.start_num,
                                        end_num=args.end_num,
                                        mod_boundary=args.mod_boundary,
                                        increment=args.increment,
                                        explain=args.explain)
            gf[i] = br
        file_groups = gf

    if args.check in ["dirs", "both"]:
        cd = collect_dirs(args.dir, args.exclude, args.recursive)
        gd = group_items(cd, args, "dirs")
        for i,g in enumerate(gd):
            br = detect_breaks_in_group(g,
                                        start_num=args.start_num,
                                        end_num=args.end_num,
                                        mod_boundary=args.mod_boundary,
                                        increment=args.increment,
                                        explain=args.explain)
            gd[i] = br
        dir_groups = gd

    all_results = file_groups + dir_groups

    # 2) format
    final_str = format_results(all_results, args)

    # 3) output
    outs = set(args.output) if args.output else {"stdout"}
    if "all" in outs:
        outs = {"stdout", "file", "clip"}

    # default filename
    tzname = time.tzname[time.localtime().tm_isdst]
    def_name = datetime.now().strftime(f"pattern_break_%y.%m.%d_%H-%M_{tzname}.txt")
    out_file = args.filename if args.filename else def_name

    if "file" in outs:
        with open(out_file,"w",encoding="utf-8") as f:
            f.write(final_str)
        print(f"[pattern-break] Wrote output to file: {out_file}", file=sys.stderr)

    if "clip" in outs:
        if HAS_PYPERCLIP:
            pyperclip.copy(final_str)
            print("[pattern-break] Copied output to clipboard.", file=sys.stderr)
        else:
            print("[pattern-break] pyperclip not installed; cannot copy to clipboard.", file=sys.stderr)

    if not args.quiet and "stdout" in outs:
        print(final_str)

if __name__ == "__main__":
    main()
