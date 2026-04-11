# DICOM to NIfTI Toolkit

A fast and modular command-line toolkit for processing medical imaging datasets. It simplifies batch DICOM-to-NIfTI conversion, ensures data integrity through strict spatial validation, and allows for highly customizable output organization via pluggable naming strategies.

## Features

- **Batch Conversion**: Fast DICOM to NIfTI transformation with automatic RAS reorientation.
- **Strict Validation**: Post-conversion QA comparing dimensions and voxel spacing against original DICOM headers.
- **Dimension Analysis**: Generates detailed reports on spatial uniformity, detecting both dimensional and voxel spacing outliers across NIfTI and DICOM datasets.
- **Pluggable Strategies**: Organize NIfTI files into flexible directory layouts (Flat, Mirror, Map).
- **Lightweight Architecture**: Analyzes datasets by reading medical headers only, preventing RAM overload.
- **Clean CLI**: Standardized, progress-bar-equipped console outputs across all tools.

## Prerequisites

- **Python 3.10+**
- **Data Format**: Your source DICOM files must have the `.dcm` extension. The toolkit's recursive scanner explicitly searches for `*.dcm` to identify image series.

## Installation

Install using `uv` (recommended) or standard `pip` and the provided requirements file:

```bash
# Using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# Using pip
pip install -r requirements.txt
```

## Quick Start

### 1. Converting DICOMs to NIfTI
Process your entire DICOM dataset at once. Outputs default to a flat directory structure.

```bash
python convert.py /path/to/dicoms -s /path/to/output_nifti
```

### 2. Validating Conversions
Ensure the converted NIfTI files match the spatial properties (shape and voxel spacing) of the source DICOMs, and verify overall dataset uniformity.

```bash
python validate.py /path/to/dicoms /path/to/output_nifti
```

### 3. Analyzing Dataset Dimensions
Generates a detailed report for any DICOM or NIfTI dataset. The tool evaluates spatial uniformity by grouping unique 3D image matrices and physical voxel spacings (in mm). It provides frequency counts of in-plane resolutions (X, Y) and slice depths (Z), detects outliers based on both dimensions and voxel spacings, and includes a detailed inventory of every processed volume.

```bash
# Analyze NIfTI files
python analyze.py --nifti /path/to/output_nifti

# Analyze DICOM datasets
python analyze.py --dicom /path/to/dicoms

# Save analysis report to a text file
python analyze.py --dicom /path/to/dicoms -s report.txt
```

## CLI Reference

#### `convert.py`

**Usage:** `python convert.py <dicom_dir> -s <save_dir> [options]`

| Argument | Required | Description |
|----------|----------|-------------|
| `<dicom_dir>` | Yes (Positional) | Root directory containing input DICOM series. |
| `-s`, `--save` | Yes | Output directory where NIfTI files will be saved. |
| `--mode` | No | Output structure mode: `flat`, `mirror`, or `map` (default: `flat`). |
| `--sep` | No | *(Strategy: flat)* Separator character for filenames (default: `@`). |
| `--prefix` | No | *(Strategy: map)* Base filename prefix (default: `vol`). |

#### `validate.py`

**Usage:** `python validate.py <dicom_dir> <nifti_dir> [options]`

| Argument | Required | Description |
|----------|----------|-------------|
| `<dicom_dir>` | Yes (Positional) | Root directory containing original DICOM series. |
| `<nifti_dir>` | Yes (Positional) | Directory containing converted NIfTI files. |
| `--mode` | No | Naming strategy used during conversion (default: `flat`). |
| `--sep` | No | *(Strategy: flat)* Separator character that was used (default: `@`). |

#### `analyze.py`

**Usage:** `python analyze.py (--nifti <dir> | --dicom <dir>) [-s <report.txt>]`

| Argument | Required | Description |
|----------|----------|-------------|
| `--nifti` | Conditional | Directory containing `.nii.gz` files to analyze. *(Either this or `--dicom` is required)* |
| `--dicom` | Conditional | Root directory containing DICOM series to analyze. *(Either this or `--nifti` is required)* |
| `-s`, `--save` | No | Save the analysis report to a text file at the given path. |

## Naming Strategies

The toolkit uses **Naming Strategies** to decide how generated NIfTI files are named and organized. Select a strategy via the `--mode` flag.

| Mode | Behavior | Example Input | Example Output |
|------|----------|---------------|----------------|
| `flat` | All NIfTI files are placed in a single directory. The original directory structure is encoded directly into the filename using a specified separator. | `patient_1/head/scan` | `output/patient_1@head@scan.nii.gz` |
| `mirror` | Recreates the original folder structure in the output. | `patient_1/head/scan` | `output/patient_1/head/scan.nii.gz` |
| `map` | Produces sequentially numbered filenames and saves a JSON mapping file to trace each NIfTI file back to its original DICOM path. | `patient_1/head/scan` | `output/vol_1.nii.gz` + `dataset_map.json` |

### Strategy Arguments

You can pass strategy-specific adjustments directly in the CLI:

```bash
# Use 'flat' mode with a custom separator
python convert.py dicoms/ -s nifti/ --mode flat --sep "_"

# Use 'map' mode with a custom prefix
python convert.py dicoms/ -s nifti/ --mode map --prefix "subject"
```

### Building Custom Naming Strategies

Build custom directory layouts by extending the abstract `NamingStrategy` base class. This base module defines the required methods (`build_output_path` and `resolve_nifti_path`) that any custom naming strategy must implement to be compatible with the converter and validator scripts.

To add a new naming mode:

1. **Create your strategy file** (`naming/my_strategy.py`) containing a class inheriting from `NamingStrategy`:

```python
from pathlib import Path
from naming.base import NamingStrategy

class CustomStrategy(NamingStrategy):
    """Defines custom naming rules for organizing NIfTI outputs."""

    def build_output_path(self, output_dir: Path, relative_path: Path, index: int) -> Path:
        """Generates the target save path for the converted NIfTI file."""
        target_name = f"custom_{relative_path.name}.nii.gz"
        return output_dir / target_name

    def resolve_nifti_path(self, output_dir: Path, relative_path: Path) -> Path | None:
        """Resolves the expected NIfTI path during dataset validation."""
        # Add your reverse lookup implementation here
        return output_dir / f"custom_{relative_path.name}.nii.gz"
```

2. **Register the strategy** (in `naming/__init__.py`):
Import your custom strategy and add one entry to the `STRATEGIES` dict.

```python
from naming.my_strategy import CustomStrategy

STRATEGIES = {
    "flat": FlatStrategy,
    "mirror": MirrorStrategy,
    "map": MapStrategy,
    "custom": CustomStrategy  # Available via --mode custom
}
```

## Project Structure

```text
dicom-to-nifti-toolkit/
├── convert.py              - CLI: DICOM to NIfTI converter
├── validate.py             - CLI: Post-conversion QA
├── analyze.py              - CLI: Dataset dimension and spacing analysis
├── utils.py                - Shared utilities
├── naming/                 - Pluggable naming strategies
│   ├── __init__.py         - Strategy registry
│   ├── base.py             - Abstract base class interface
│   ├── flat.py             - Flat directory strategy
│   ├── mirror.py           - Mirror directory strategy
│   └── map_strategy.py     - JSON-mapped sequential strategy
└── requirements.txt        - Python dependencies
```