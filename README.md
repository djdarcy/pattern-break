# Pattern-Break

**Pattern-Break** detects numeric gaps in filenames or directory names. Designed for developers, data managers, artists, photographers, and archivists, it offers powerful features for analyzing sequences, expanding ranges, and producing detailed reports. Whether you need to look for missing images, manage backups, or enforce naming conventions, `pattern-break` can help to identify gaps in many datasets.

## Features

- **Numeric Gap Detection**: Identifies missing numeric sequences in files and directories.
- **Multi-Block Analysis**: Handles filenames with multiple numeric blocks using advanced policies.
- **Range Expansion**: Detects and integrates numeric ranges within standalone filenames, like `100-120`, into the analysis.
- **Recursive Directory Scanning**: Analyzes subdirectories when needed.
- **Flexible Grouping**: Groups results by directory or across directories for cross-analysis.
- **Threshold Splitting**: Divides groups based on large numeric gaps.
- **Customizable Outputs**: Generates results in various formats:
  - Summary
  - Inline
  - CSV
  - JSON
  - ASCII table
  - Rich table (with ANSI support)
- **Output Destinations**: Redirect results to the console, files, or clipboard.

## Typical Use Cases

1. **Dataset Validation**

   - Ensure sequential file naming without gaps in datasets or archives.

2. **Backup and Restore**

   - Verify integrity and completeness of backups by identifying missing files.

3. **Project Management**

   - Audit files across directories for missing versions or incomplete series.

4. **Archival Compliance**

   - Enforce numeric naming conventions in long-term storage solutions.

## Installation

#### **Clone the Repository**:

```bash
git clone https://github.com/dustinjd/pattern-break.git
cd pattern-break
```

#### **Install Dependencies**:

Install required libraries via pip:

```bash
pip install pyperclip rich
```

- `pyperclip`: Enables clipboard integration.
- `rich`: Provides rich-text table formatting.

## Usage Examples

#### Common Compound Command ####

```bash
pattern-break.py --check both -d . -r -gt 100 --multi-range -fmt summary --stats -o stdout -xd .git -xd .sync -o file -f missing.txt
```
Searches the for pattern breaks in filenames and folder names (`--check both`) starting from the current directory (`-d .`) recursively (`-r`), excluding git folders and sync folders, (`-xd .git -xd .sync`), for patterns matching a group threshhold of 100 files (`-gt 100`), looking for in-filename patterns as well (`--multi-range`), formatting the output in a JSON-like summary format (`-fmt summary`) showing statistics (`--stats`) and outputting to the console (`-o stdout`) and to file (`-o file -f missing.txt`)


#### Basic Gap Detection

```bash
python pattern-break.py -d /path/to/files --format=summary
```
For a list of files like `001.txt, 002.txt, 003.txt, 004.txt, 006.txt, 008.txt` would identify `005.txt` and `007.txt`

#### Multi-Range Expansion

```bash
python pattern-break.py -d /path/to/files --multi-range
```
For a list of files like `001.txt, 002-004.txt, 006.txt, 008.txt` would identify `005.txt` and `007.txt`

#### Cross-Directory Analysis

```bash
python pattern-break.py -d /dir1 /dir2 --cross-dir-grouping
```
As the name suggests would find patterns even across folders, so if `005.txt` or `007.txt` existed in dir2 it would count them as part of the sequence.

#### CSV Output

```bash
python pattern-break.py -d /path/to/files --format=csv -o file --filename gaps.csv
```

#### Threshold Splitting

```bash
python pattern-break.py -d /path/to/files --group-threshold 50
```
This means that if there are files named 001.txt to 100.txt it would treat 001.txt to 050.txt as one logical group, and 051.txt to 100.txt as a distinct group when trying to identify missing files.

## Command Reference

| Argument              | Description                                                  |
| --------------------- | ------------------------------------------------------------ |
| `--check`             | Analyze `files`, `dirs`, or `both` (default=files)           |
| `--pattern`           | Only include regex filter matching names.                    |
| `-xd`, `--exclude`    | Exclude patterns (e.g. *.txt)                                |
| `-d, --dir`           | Directories to scan.                                         |
| `-r, --recursive`     | Include subdirectories in the scan.                          |
| `--multi-range`       | Expand numeric ranges in filenames.                          |
| `--block-policy`      | Policy for handling numeric blocks (e.g., `first`, `all`).   |
| `--group-threshold`   | Split groups if numeric gap > threshold                      |
| `--cross-dir-grouping`| Merge coverage from multiple dirs if numeric values align.   |
| `--start-num`         | Force sequence start.                                        |
| `--end-num`           | Force sequence end.                                          |
| `--mod-boundary`      | Consider missing up to next boundary (e.g. mod=100)          |
| `-inc`, `--increment` | Step between consecutive numbers (default=1)                 |
| `--format`            | Output format (`summary`, `inline`, `CSV`, `JSON`, etc.).    |
| `-o, --output`        | Destination for output (`stdout`, `file`, `clipboard`).      |
| `--range`             | Display missing ranges (`compact`, `all` in detail).         |
| `--range-fmt`         | Blank lines between segments? (`spacing`, `nospace`)         |
| `-v`, `--verbose`     | Provide additional debugging information.                    |
| `-q`, `--quiet`       | Supresses stdout                                             |

Run `pattern-break.py --help` for a complete list of arguments.

## Contributing

Contributions to `Pattern-Break` are welcome! To contribute:

1. Fork this repository and clone it.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a clear description of your changes.

Like the project?

[!["Buy Me A Coffee"](https://camo.githubusercontent.com/0b448aabee402aaf7b3b256ae471e7dc66bcf174fad7d6bb52b27138b2364e47/68747470733a2f2f7777772e6275796d6561636f666665652e636f6d2f6173736574732f696d672f637573746f6d5f696d616765732f6f72616e67655f696d672e706e67)](https://www.buymeacoffee.com/djdarcy)

## License

pattern-break.py, Copyright (C) 2025 Dustin Darcy

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.

