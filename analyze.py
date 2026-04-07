"""Dataset dimension analyzer for NIfTI and DICOM.

Scans a folder of NIfTI files or DICOM series, collects spatial dimensions
and voxel resolutions, detects outliers, and generates a summary report.
"""
import argparse
from pathlib import Path
from typing import NamedTuple
import nibabel as nib
import numpy as np
import pydicom
from tqdm import tqdm

from utils import find_dicom_directories

class VolumeInfo(NamedTuple):
    name: str
    shape: tuple
    spacing: tuple


def scan_nifti_directory(nifti_dir: Path) -> list[VolumeInfo]:
    """Parses dimensions and spacing from all NIfTI files in a directory.

    Args:
        nifti_dir: The root directory to scan for .nii.gz files.

    Returns:
        A list of VolumeInfo objects containing spatial properties for each discovered NIfTI file.
    """
    nifti_files = sorted(nifti_dir.rglob("*.nii.gz"))

    if not nifti_files:
        raise FileNotFoundError(f"No .nii.gz files found in {nifti_dir}")

    volumes = []
    for nii_path in tqdm(nifti_files, desc="Scanning NIfTI", unit="file"):
        try:
            nii = nib.load(str(nii_path))
            shape = nii.shape[:3]
            spacing = tuple(round(float(z), 3) for z in nii.header.get_zooms()[:3])

            rel_name = str(nii_path.relative_to(nifti_dir))
            volumes.append(VolumeInfo(rel_name, shape, spacing))
        except Exception as e:
            tqdm.write(f"Error reading {nii_path.name}: {e}")

    return volumes


def scan_dicom_directory(dicom_root: Path) -> list[VolumeInfo]:
    """Parses dimensions and spacing directly from DICOM series headers.

    Args:
        dicom_root: The root directory to scan for DICOM series.

    Returns:
        A list of VolumeInfo objects containing spatial properties for each discovered DICOM series.
    """
    dicom_dirs = find_dicom_directories(dicom_root)

    if not dicom_dirs:
        raise FileNotFoundError(f"No DICOM directories found in {dicom_root}")

    volumes = []
    for dicom_dir in tqdm(dicom_dirs, desc="Scanning DICOM", unit="series"):
        try:
            dcm_files = list(dicom_dir.glob("*.dcm"))
            ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)

            shape = (
                getattr(ds, "Columns", 0),
                getattr(ds, "Rows", 0),
                len(dcm_files),
            )

            pixel_spacing = getattr(ds, "PixelSpacing", [0.0, 0.0])
            slice_thickness = getattr(ds, "SliceThickness", 0.0)
            spacing_between_slices = getattr(ds, "SpacingBetweenSlices", slice_thickness)
            spacing = (
                round(float(pixel_spacing[0]), 3),
                round(float(pixel_spacing[1]), 3),
                round(abs(float(spacing_between_slices)), 3),
            )

            rel_name = str(dicom_dir.relative_to(dicom_root))
            volumes.append(VolumeInfo(rel_name, shape, spacing))
        except Exception as e:
            tqdm.write(f"Error reading {dicom_dir.name}: {e}")

    return volumes


def find_outliers(volumes: list[VolumeInfo]) -> list[VolumeInfo]:
    """Identifies volumes whose spatial dimensions deviate significantly from the dataset norm.

    An outlier is defined as any volume where at least one spatial dimension differs
    from the median dimension by more than two standard deviations.

    Args:
        volumes: A list of VolumeInfo objects representing the dataset.

    Returns:
        A list of VolumeInfo objects flagged as outliers.
    """
    if len(volumes) < 5:
        return []

    shapes = np.array([v.shape for v in volumes])
    medians = np.median(shapes, axis=0)
    stds = np.std(shapes, axis=0)

    outliers = []
    for vol in volumes:
        deviations = np.abs(np.array(vol.shape) - medians)
        if np.any(deviations > 2 * stds + 1e-9):
            outliers.append(vol)

    return outliers


def build_report(volumes: list[VolumeInfo], outliers: list[VolumeInfo], source_type: str) -> str:
    """Generates a text report summarizing dataset dimensions and potential issues.

    Args:
        volumes: A list of VolumeInfo objects for the dataset.
        outliers: A subset of VolumeInfo objects flagged as dimensional outliers.
        source_type: A descriptive string indicating the data source (e.g., "NIfTI", "DICOM").

    Returns:
        A formatted string containing the full analysis report.
    """
    shapes = set(v.shape for v in volumes)
    spacings = set(v.spacing for v in volumes)

    lines: list[str] = []

    lines.append(f"{'-' * 60}")
    lines.append(f"Dataset Dimension Analysis ({source_type})")
    lines.append(f"{'-' * 60}")
    lines.append(f"Total volumes:   {len(volumes)}")
    lines.append(f"{'-' * 60}")

    # Shape summary
    lines.append("Dimensions")
    lines.append(f"{'-' * 60}")
    if len(shapes) == 1:
        lines.append(f"Uniform - all volumes: {list(shapes)[0]}")
    else:
        lines.append(f"Warning: {len(shapes)} unique dimension groups:")
        shape_counts: dict[tuple, int] = {}
        for v in volumes:
            shape_counts[v.shape] = shape_counts.get(v.shape, 0) + 1
        for shape, count in sorted(shape_counts.items(), key=lambda s: s[1], reverse=True):
            lines.append(f"{shape}  x{count}")
    lines.append(f"{'-' * 60}")

    # Spacing summary
    lines.append("Voxel Spacing")
    lines.append(f"{'-' * 60}")
    if len(spacings) == 1:
        lines.append(f"Uniform - all volumes: {list(spacings)[0]} mm")
    else:
        lines.append(f"Warning: {len(spacings)} unique voxel spacings:")
        spacing_counts: dict[tuple, int] = {}
        for v in volumes:
            spacing_counts[v.spacing] = spacing_counts.get(v.spacing, 0) + 1
        for spc, count in sorted(spacing_counts.items(), key=lambda v: v[1], reverse=True):
            lines.append(f"{spc} mm  x{count}")
    lines.append(f"{'-' * 60}")

    # Outlier report
    lines.append("Outliers")
    lines.append(f"{'-' * 60}")
    if outliers:
        lines.append(f"{len(outliers)} outlier(s) detected:")
        for vol in outliers:
            lines.append(f"- {vol.name}")
            lines.append(f"shape={vol.shape}  spacing={vol.spacing}")
    else:
        lines.append("No dimensional outliers detected.")
    lines.append(f"{'-' * 60}")

    # Dataset details
    lines.append("Dataset Details")
    lines.append(f"{'-' * 60}")
    idx_width = len(str(len(volumes)))
    for i, vol in enumerate(volumes, start=1):
        lines.append(f"[{i:>{idx_width}}] {vol.name}")
        lines.append(f"shape={vol.shape}  spacing={vol.spacing}")

    lines.append(f"{'-' * 60}")
    return "\n".join(lines)



def main():
    parser = argparse.ArgumentParser(
        prog="analyze",
        description=(
            "Analyze dimensions and voxel spacings of a medical imaging dataset. "
            "Supports both NIfTI and DICOM input. Detects outliers and reports uniformity."
        ),
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--nifti", help="Directory containing .nii.gz files")
    source.add_argument("--dicom", help="Root directory containing DICOM series")
    parser.add_argument("-s", "--save", help="Save report to a text file")
    args = parser.parse_args()

    if args.nifti:
        nifti_dir = Path(args.nifti).resolve()
        if not nifti_dir.is_dir():
            raise NotADirectoryError(f"Directory does not exist: {nifti_dir}")
        print(f"\nScanning NIfTI: {nifti_dir}\n")
        vols = scan_nifti_directory(nifti_dir)
        source_type = "NIfTI"
    else:
        dicom_dir = Path(args.dicom).resolve()
        if not dicom_dir.is_dir():
            raise NotADirectoryError(f"Directory does not exist: {dicom_dir}")
        print(f"\nScanning DICOM: {dicom_dir}\n")
        vols = scan_dicom_directory(dicom_dir)
        source_type = "DICOM"

    outliers = find_outliers(vols)
    report = build_report(vols, outliers, source_type)

    print(f"\n{report}")

    if args.save:
        output_path = Path(args.save).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"\nReport saved -> {output_path}")

if __name__ == "__main__":
    main()
