# DICOM to NIfTI Toolkit

A fast and modular command-line toolkit for processing medical imaging datasets. It simplifies batch DICOM-to-NIfTI conversion, ensures data integrity through strict spatial validation, and allows for highly customizable output organization via pluggable naming strategies.

## Features

- **Batch Conversion**: Fast DICOM to NIfTI transformation with automatic RAS reorientation.
- **Strict Validation**: Post-conversion QA comparing dimensions and voxel spacing against original DICOM headers.
- **Dimension Analysis**: Scans for spatial uniformity and detects outliers across both NIfTI and DICOM datasets.
- **Pluggable Strategies**: Organize NIfTI files into flexible directory layouts (Flat, Mirror, Map).
- **Lightweight Architecture**: Analyzes datasets by reading medical headers only, preventing RAM overload.
- **Clean CLI**: Standardized, progress-bar-equipped console outputs across all tools.

## Installation

Install using pip and the provided requirements file:

```bash
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
Scan raw DICOMs or NIfTI files for dataset uniformity and outliers.

```bash
# Analyze NIfTI files
python analyze.py --nifti /path/to/output_nifti

# Analyze raw DICOM series
python analyze.py --dicom /path/to/dicoms

# Save analysis report to a text file
python analyze.py --dicom /path/to/dicoms -s report.txt
```

## Available Scripts

| Script | Purpose | Description |
|--------|---------|-------------|
| `convert.py` | Conversion | Performs DICOM-to-NIfTI format conversion using dicom2nifti. |
| `validate.py` | Validation | Validates output integrity by matching NIfTI spatial properties against source DICOM headers. |
| `analyze.py` | Auditing | Scans dataset to report dimension frequencies, spacing distributions, and detect outliers. |

## Naming Strategies

The toolkit uses **Naming Strategies** to decide how generated NIfTI files are named and organized. Select a strategy via the `--mode` flag.

| Mode | Behavior | Example Input | Example Output |
|------|----------|---------------|----------------|
| `flat` | All NIfTI files in one directory, separated by a character. | `patient_1/head/scan` | `output/patient_1@head@scan.nii.gz` |
| `mirror` | Replicates the exact directory structure of the source. | `patient_1/head/scan` | `output/patient_1/head/scan.nii.gz` |
| `map` | Sequential naming with a generated JSON registry map. | `patient_1/head/scan` | `output/vol_1.nii.gz` + `dataset_map.json` |

### Strategy Arguments

You can pass strategy-specific adjustments directly in the CLI:

```bash
# Use 'flat' mode with a custom separator
python convert.py dicoms/ -s nifti/ --mode flat --sep "_"

# Use 'map' mode with a custom prefix
python convert.py dicoms/ -s nifti/ --mode map --prefix "subject"
```

### Building Custom Naming Strategies

Build custom directory layouts by extending the `NamingStrategy` base class.

1. **Create your strategy file** (`naming/my_strategy.py`):

```python
from pathlib import Path
from naming.base import NamingStrategy

class CustomStrategy(NamingStrategy):
    """Defines custom naming rules for organizing NIfTI outputs."""

    def build_output_path(self, output_dir: Path, relative_path: Path, index: int) -> Path:
        """Generates the target save path for the converted NIfTI file."""
        target_name = f"custom_{index}.nii.gz"
        return output_dir / target_name

    def resolve_nifti_path(self, output_dir: Path, relative_path: Path) -> Path | None:
        """Resolves the expected NIfTI path during dataset validation."""
        # Add your reverse lookup implementation here
        return output_dir / f"custom_{relative_path.name}.nii.gz"
```

2. **Register the strategy** (in `naming/__init__.py`):

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
med-nifti-toolkit/
├── convert.py              - CLI: DICOM to NIfTI converter
├── validate.py             - CLI: Post-conversion QA
├── analyze.py              - CLI: Dataset dimension analysis
├── utils.py                - Shared utilities
├── naming/                 - Pluggable naming strategies
│   ├── __init__.py         - Strategy registry
│   ├── base.py             - Abstract base class interface
│   ├── flat.py             - Flat directory strategy
│   ├── mirror.py           - Mirror directory strategy
│   └── map_strategy.py     - JSON-mapped sequential strategy
└── requirements.txt        - Python dependencies
```