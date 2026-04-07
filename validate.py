"""Post-conversion check for NIfTI datasets.

Verifies that every DICOM series has a matching NIfTI file, compares spatial
metadata (dimensions, voxel sizes) against the original DICOM headers, and
reports whether the dataset has uniform dimensions.
"""
import argparse
from pathlib import Path
from typing import Optional, Tuple
import pydicom
import nibabel as nib
import numpy as np
from tqdm import tqdm

from utils import find_dicom_directories
from naming import get_strategy, available_strategies


def verify_single_pair(dicom_dir: Path, nifti_path: Path) -> tuple[bool, tuple, tuple] | None:
    """Compares spatial metadata between a DICOM series and its corresponding NIfTI file.

    Args:
        dicom_dir: Directory containing the source .dcm files.
        nifti_path: Path to the expected .nii.gz output file.

    Returns:
        A tuple containing:
            - A boolean indicating whether the spatial metadata matches.
            - A tuple representing the NIfTI dimensions (shape).
            - A tuple representing the NIfTI voxel spacing.
        Returns None if an error occurs during reading.
    """
    try:
        dcm_files = list(dicom_dir.glob("*.dcm"))
        ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)

        dicom_shape = (ds.Columns, ds.Rows, len(dcm_files))
        pixel_spacing = getattr(ds, "PixelSpacing", [0.0, 0.0])
        slice_thickness = getattr(ds, "SliceThickness", 0.0)
        spacing_between_slices = getattr(ds, "SpacingBetweenSlices", slice_thickness)
        dicom_spacing = (
            float(pixel_spacing[0]),
            float(pixel_spacing[1]),
            abs(float(spacing_between_slices)),
        )

        nii = nib.load(str(nifti_path))
        nifti_full_shape = nii.shape

        if len(nifti_full_shape) < 3:
            tqdm.write(f"ERROR: {nifti_path.name}: invalid NIfTI shape {nifti_full_shape}; expected at least 3 dimensions")
            return None
        if len(nifti_full_shape) > 3:
            tqdm.write(f"INFO: {nifti_path.name}: extra dimensions {nifti_full_shape[3:]} ignored")

        nifti_shape = nifti_full_shape[:3]
        nifti_spacing = nii.header.get_zooms()[:3]

        dim_match = (
            set(dicom_shape[:2]) == set(nifti_shape[:2])
            and dicom_shape[2] == nifti_shape[2]
        )

        d_spacings = sorted([dicom_spacing[0], dicom_spacing[1]])
        n_spacings = sorted([float(nifti_spacing[0]), float(nifti_spacing[1])])
        xy_match = np.isclose(d_spacings, n_spacings, atol=1e-3).all()
        z_match = np.isclose(
            dicom_spacing[2], float(nifti_spacing[2]), atol=1e-3
        )

        if dim_match and xy_match and z_match:
            return True, nifti_shape, nifti_spacing
        else:
            issues = []
            if not dim_match:
                issues.append(f"shape DICOM {dicom_shape} != NIfTI {nifti_shape}")
            if not xy_match:
                issues.append(f"pixel spacing DICOM {d_spacings} != NIfTI {n_spacings}")
            if not z_match:
                issues.append(
                    f"slice spacing DICOM {dicom_spacing[2]:.4f} != NIfTI {nifti_spacing[2]:.4f}"
                )
            tqdm.write(f"Mismatch: {dicom_dir.name}")
            for issue in issues:
                tqdm.write(f"    {issue}")
            return False, nifti_shape, nifti_spacing

    except Exception as e:
        tqdm.write(f"Error reading {dicom_dir.name}: {e}")
        return None


def main():
    strategies = available_strategies()

    parser = argparse.ArgumentParser(
        prog="validate",
        description=(
            "Verify NIfTI spatial metadata against original DICOMs. "
            "Checks dataset dimensional uniformity."
        ),
        epilog="Provide input DICOM directory and input NIfTI directory.",
    )
    parser.add_argument("dicom_dir", help="Root directory containing DICOM series")
    parser.add_argument("nifti_dir", help="Directory containing converted NIfTI files")
    parser.add_argument("--mode", choices=strategies, default="flat",
        help=f"Directory structure mode used during conversion (default: flat). Available: {strategies}")
    parser.add_argument("--sep", default="@",
        help="Separator for compatible naming strategies (default: '@')")
    args = parser.parse_args()

    dicom_root = Path(args.dicom_dir).resolve()
    nifti_root = Path(args.nifti_dir).resolve()

    if not dicom_root.is_dir() or not nifti_root.is_dir():
        raise NotADirectoryError("Both arguments must be existing directories.")

    dicom_dirs = find_dicom_directories(dicom_root)
    if not dicom_dirs:
        raise FileNotFoundError(f"No DICOM directories found in {dicom_root}")

    strategy_kwargs = {}
    if args.mode == "flat":
        strategy_kwargs["sep"] = args.sep
    strategy = get_strategy(args.mode, **strategy_kwargs)

    if args.mode == "map":
        strategy.load_map(nifti_root)

    total = len(dicom_dirs)
    match_count = 0
    mismatch_count = 0
    missing_count = 0
    error_count = 0
    nifti_shapes = set()
    nifti_spacings = set()

    print(f"\n{'-' * 60}")
    print("DICOM vs NIfTI Validation")
    print(f"{'-' * 60}")
    print(f"DICOM source:  {dicom_root}")
    print(f"NIfTI output:  {nifti_root}")
    print(f"Mode:          {args.mode}")
    print(f"Items:         {total}")
    print(f"{'-' * 60}\n")

    progress = tqdm(enumerate(dicom_dirs, start=1), total=total, unit="series", desc="Validating")

    for i, dicom_dir in progress:
        relative_path = dicom_dir.relative_to(dicom_root)
        if relative_path == Path("."):
            relative_path = Path(dicom_dir.name)
        progress.set_postfix_str(f"{relative_path}")

        nifti_path = strategy.resolve_nifti_path(nifti_root, relative_path)

        if nifti_path is None:
            missing_count += 1
            tqdm.write(f"Warning: No mapping found: {relative_path}")
            progress.set_postfix_str(f"{relative_path} [SKIP]")
            continue

        if not nifti_path.exists():
            missing_count += 1
            tqdm.write(f"Warning: Missing file: {nifti_path.name}")
            progress.set_postfix_str(f"{relative_path} [MISS]")
            continue

        result = verify_single_pair(dicom_dir, nifti_path)
        if result is None:
            error_count += 1
        else:
            is_match, shape, spacing = result
            if is_match:
                match_count += 1
            else:
                mismatch_count += 1
            nifti_shapes.add(shape)
            nifti_spacings.add((
                round(float(spacing[0]), 3),
                round(float(spacing[1]), 3),
                round(float(spacing[2]), 3),
            ))

    # Summary
    print(f"\n{'-' * 60}")
    print("Validation Summary")
    print(f"{'-' * 60}")
    print(f"Matched:     {match_count}/{total}")
    if mismatch_count > 0:
        print(f"Mismatched:  {mismatch_count}/{total}")
    if missing_count > 0:
        print(f"Missing:     {missing_count}/{total}")
    if error_count > 0:
        print(f"Errors:      {error_count}/{total}")
    print(f"{'-' * 60}")

    if nifti_shapes or nifti_spacings:
        print("Dataset Consistency:")
        print(f"{'-' * 60}")
        if nifti_shapes:
            if len(nifti_shapes) == 1:
                print(f"Shape:    Uniform - {list(nifti_shapes)[0]}")
            else:
                print(f"Shape:    Warning: {len(nifti_shapes)} unique dimensions found:")
                for shape in sorted(nifti_shapes):
                    print(f" - {shape}")

        if nifti_spacings:
            if len(nifti_spacings) == 1:
                print(f"Spacing:  Uniform - {list(nifti_spacings)[0]} mm")
            else:
                print(f"Spacing:  Warning: {len(nifti_spacings)} unique spacings found:")
                for spc in sorted(nifti_spacings):
                    print(f" - {spc} mm")

if __name__ == "__main__":
    main()
