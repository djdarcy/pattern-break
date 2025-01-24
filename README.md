# Pattern-Break

**Pattern-Break** is a handy tool for detecting numeric gaps in filenames or directory names. Designed for developers, data managers, artists, photographers, and archivists, it offers powerful features for analyzing sequences, expanding ranges, and producing detailed reports. Whether you need to validate a datasets, manage backups, or enforce naming conventions, Pattern-Break is an indispensable utility.

## Features

- **Numeric Gap Detection**: Identifies missing numeric sequences in files and directories.
- **Multi-Block Analysis**: Handles filenames with multiple numeric blocks using advanced policies.
- **Range Expansion**: Detects and integrates numeric ranges like `100-120` into the analysis.
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

#### Basic Gap Detection

```bash
python pattern-break.py -d /path/to/files --format=summary
```

#### Multi-Range Expansion

```bash
python pattern-break.py -d /path/to/files --multi-range
```

#### Cross-Directory Analysis

```bash
python pattern-break.py -d /dir1 /dir2 --cross-dir-grouping
```

#### CSV Output

```bash
python pattern-break.py -d /path/to/files --format=csv -o file --filename gaps.csv
```

#### Threshold Splitting

```bash
python pattern-break.py -d /path/to/files --group-threshold 50
```

## Command Reference

| Argument          | Description                                                |
| ----------------- | ---------------------------------------------------------- |
| `-d, --dir`       | Directories to scan.                                       |
| `-r, --recursive` | Include subdirectories in the scan.                        |
| `--multi-range`   | Expand numeric ranges in filenames.                        |
| `--block-policy`  | Policy for handling numeric blocks (e.g., `first`, `all`). |
| `--format`        | Output format (summary, inline, CSV, JSON, etc.).          |
| `-o, --output`    | Destination for output (stdout, file, clipboard).          |
| `--range`         | Display missing ranges compactly or in detail.             |
| `--verbose`       | Provide additional debugging information.                  |

Run `pattern-break.py --help` for a complete list of arguments.

## Contributing

We welcome contributions to **Pattern-Break**! To contribute:

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

