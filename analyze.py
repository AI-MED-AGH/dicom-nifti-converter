import argparse
import textwrap
from pathlib import Path
from typing import NamedTuple
import nibabel as nib
import numpy as np
import pydicom
from tqdm import tqdm

from utils import find_dicom_directories

SEPARATOR = "━" * 80

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


def find_dimension_outliers(volumes: list[VolumeInfo]) -> list[VolumeInfo]:
    """Identifies volumes whose spatial dimensions deviate significantly from the dataset norm.

    An outlier is defined as any volume where at least one spatial dimension differs
    from the median dimension by more than two standard deviations.

    Args:
        volumes: A list of VolumeInfo objects representing the dataset.

    Returns:
        A list of VolumeInfo objects flagged as dimensional outliers.
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


def find_spacing_outliers(volumes: list[VolumeInfo]) -> list[VolumeInfo]:
    """Identifies volumes whose voxel spacings deviate significantly from the dataset norm.

    An outlier is defined as any volume where at least one spacing component differs
    from the median spacing by more than two standard deviations.

    Args:
        volumes: A list of VolumeInfo objects representing the dataset.

    Returns:
        A list of VolumeInfo objects flagged as spacing outliers.
    """
    if len(volumes) < 5:
        return []

    spacings = np.array([v.spacing for v in volumes])
    medians = np.median(spacings, axis=0)
    stds = np.std(spacings, axis=0)

    outliers = []
    for vol in volumes:
        deviations = np.abs(np.array(vol.spacing) - medians)
        if np.any(deviations > 2 * stds + 1e-9):
            outliers.append(vol)

    return outliers


def build_report(volumes: list[VolumeInfo], dim_outliers: list[VolumeInfo], spc_outliers: list[VolumeInfo], source_type: str) -> str:
    """Generates a text report summarizing dataset dimensions and potential issues.

    Args:
        volumes: A list of VolumeInfo objects for the dataset.
        dim_outliers: A subset of VolumeInfo objects flagged as dimensional outliers.
        spc_outliers: A subset of VolumeInfo objects flagged as spacing outliers.
        source_type: A descriptive string indicating the data source (e.g., "NIfTI", "DICOM").

    Returns:
        A formatted string containing the full analysis report.
    """
    shapes = set(v.shape for v in volumes)
    spacings = set(v.spacing for v in volumes)

    lines: list[str] = []

    lines.append(SEPARATOR)
    lines.append(f"Dataset Dimension Analysis ({source_type})")
    lines.append(SEPARATOR)
    lines.append(f"Total volumes:   {len(volumes)}")
    lines.append(SEPARATOR)

    # Shape summary
    lines.append("Dimensions")
    lines.append(SEPARATOR)
    if len(shapes) == 1:
        lines.append(f"Uniform - all volumes: {list(shapes)[0]}")
    else:
        lines.append(f"Warning: {len(shapes)} unique 3D dimension groups:")
        shape_counts: dict[tuple, int] = {}
        for v in volumes:
            shape_counts[v.shape] = shape_counts.get(v.shape, 0) + 1
        
        max_shape_len = max(len(str(shape)) for shape in shape_counts.keys())
        for shape, count in sorted(shape_counts.items(), key=lambda s: s[1], reverse=True):
            lines.append(f"    - {str(shape):<{max_shape_len}}  x{count}")

        # Resolutions
        xy_counts: dict[tuple, int] = {}
        for v in volumes:
            xy = v.shape[:2]
            xy_counts[xy] = xy_counts.get(xy, 0) + 1
            
        if len(xy_counts) == 1:
            lines.append(f"\n  Resolution (X, Y) uniform: {list(xy_counts.keys())[0]}")
        else:
            lines.append(f"\n  Resolution (X, Y) groups:")
            max_xy_len = max(len(str(xy)) for xy in xy_counts.keys())
            for xy, count in sorted(xy_counts.items(), key=lambda s: s[1], reverse=True):
                lines.append(f"    - {str(xy):<{max_xy_len}}  x{count}")

        # Slices counts
        z_counts: dict[int, int] = {}
        for v in volumes:
            z = v.shape[2]
            z_counts[z] = z_counts.get(z, 0) + 1
            
        if len(z_counts) == 1:
            lines.append(f"\n  Slice Count (Z) uniform: {list(z_counts.keys())[0]}")
        else:
            lines.append("\n  Slice Count (Z) groups:")
            sorted_z = sorted(z_counts.items(), key=lambda x: x[1], reverse=True)
            z_strs = [f"{z}\xa0(x{count})" for z, count in sorted_z]
            z_line = ", ".join(z_strs)
            
            for w in textwrap.wrap(z_line, width=76):
                lines.append(f"    {w.replace(chr(160), ' ')}")
    lines.append(SEPARATOR)

    # Spacing summary
    lines.append("Voxel Spacing")
    lines.append(SEPARATOR)
    if len(spacings) == 1:
        lines.append(f"Uniform - all volumes: {list(spacings)[0]} mm")
    else:
        lines.append(f"Warning: {len(spacings)} unique voxel spacings:")
        spacing_counts: dict[tuple, int] = {}
        for v in volumes:
            spacing_counts[v.spacing] = spacing_counts.get(v.spacing, 0) + 1
            
        max_spc_len = max(len(str(spc)) for spc in spacing_counts.keys())
        for spc, count in sorted(spacing_counts.items(), key=lambda v: v[1], reverse=True):
            lines.append(f"    - {str(spc):<{max_spc_len}} mm  x{count}")
    lines.append(SEPARATOR)

    # Dimension outlier report
    lines.append("Dimension Outliers")
    lines.append(SEPARATOR)
    if dim_outliers:
        lines.append(f"{len(dim_outliers)} outlier(s) detected:")
        max_outlier_shape_len = max(len(str(vol.shape)) for vol in dim_outliers)
        for vol in dim_outliers:
            lines.append(f"    - {vol.name}")
            lines.append(f"      shape={str(vol.shape):<{max_outlier_shape_len}}  spacing={vol.spacing}")
    else:
        lines.append("No dimensional outliers detected.")
    lines.append(SEPARATOR)

    # Spacing outlier report
    lines.append("Spacing Outliers")
    lines.append(SEPARATOR)
    if spc_outliers:
        lines.append(f"{len(spc_outliers)} outlier(s) detected:")
        max_outlier_spc_len = max(len(str(vol.spacing)) for vol in spc_outliers)
        for vol in spc_outliers:
            lines.append(f"    - {vol.name}")
            lines.append(f"      spacing={str(vol.spacing):<{max_outlier_spc_len}} mm  shape={vol.shape}")
    else:
        lines.append("No spacing outliers detected.")
    lines.append(SEPARATOR)

    # Dataset details
    lines.append("Dataset Details")
    lines.append(SEPARATOR)
    idx_width = len(str(len(volumes)))
    max_shape_len = max(len(str(vol.shape)) for vol in volumes) if volumes else 0
    for i, vol in enumerate(volumes, start=1):
        lines.append(f"[{i:>{idx_width}}] {vol.name}")
        lines.append(f"      shape={str(vol.shape):<{max_shape_len}}  spacing={vol.spacing}")

    lines.append(SEPARATOR)
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

    dim_outliers = find_dimension_outliers(vols)
    spc_outliers = find_spacing_outliers(vols)
    report = build_report(vols, dim_outliers, spc_outliers, source_type)

    print(f"\n{report}")

    if args.save:
        output_path = Path(args.save).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"\nReport saved -> {output_path}")

if __name__ == "__main__":
    main()
