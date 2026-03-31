"""
This script verifies that all DICOM files were successfully converted to NIfTI format.
It checks:
1. If every DICOM folder has a corresponding NIfTI file.
2. If the dimensions and voxel sizes match the original headers.
3. If the entire dataset has uniform dimensions.
"""
import argparse
from pathlib import Path
import pydicom
import nibabel as nib
import numpy as np
from typing import Optional, Tuple


def find_dicom_directories(root_dir: Path) -> list[Path]:
    dicom_dirs = []
    for path in root_dir.iterdir():
        if not path.is_dir() or path.name.startswith(".") or path.name in {"__pycache__"}:
            continue
        if list(path.glob("*.dcm")):
            dicom_dirs.append(path)
        else:
            dicom_dirs.extend(find_dicom_directories(path))
    return dicom_dirs

def verify_single_pair(dicom_dir: Path, nifti_path: Path) -> Optional[Tuple[bool, tuple, tuple]]:
    try:
        dcm_files = list(dicom_dir.glob("*.dcm"))
        ds = pydicom.dcmread(str(dcm_files[0]), stop_before_pixels=True)
        
        dicom_shape = (ds.Columns, ds.Rows, len(dcm_files))
        pixel_spacing = getattr(ds, 'PixelSpacing', [0.0, 0.0])
        slice_thickness = getattr(ds, 'SliceThickness', 0.0)
        spacing_between_slices = getattr(ds, 'SpacingBetweenSlices', slice_thickness)
        dicom_spacing = (float(pixel_spacing[0]), float(pixel_spacing[1]), abs(float(spacing_between_slices)))

        nii = nib.load(str(nifti_path))
        nifti_full_shape = nii.shape
        if len(nifti_full_shape) < 3:
            print(f"{dicom_dir.name}: NIfTI volume has fewer than 3 dimensions: {nifti_full_shape}")
            return None
        if len(nifti_full_shape) > 3:
            print(f"Note: NIfTI {nifti_path.name} has extra non-spatial dimensions {nifti_full_shape[3:]}, "
                  f"using spatial shape {nifti_full_shape[:3]} for comparison.")
        nifti_shape = nifti_full_shape[:3]
        nifti_spacing = nii.header.get_zooms()[:3] 

        dim_match = set(dicom_shape[:2]) == set(nifti_shape[:2]) and dicom_shape[2] == nifti_shape[2]
        
        d_spacings = sorted([dicom_spacing[0], dicom_spacing[1]])
        n_spacings = sorted([float(nifti_spacing[0]), float(nifti_spacing[1])])
        xy_match = np.isclose(d_spacings, n_spacings, atol=1e-3).all()
        z_match = np.isclose(dicom_spacing[2], float(nifti_spacing[2]), atol=1e-3)

        if dim_match and xy_match and z_match:
            print(f"Match OK: {dicom_dir.name}")
            return True, nifti_shape, nifti_spacing
        else:
            print(f"Mismatch found in: {dicom_dir.name}")
            if not dim_match:
                print(f"  Shape difference: DICOM {dicom_shape} vs NIfTI {nifti_shape}")
            if not xy_match:
                print(f"  Pixel spacing difference: DICOM {d_spacings} vs NIfTI {n_spacings}")
            if not z_match:
                print(f"  Slice spacing difference: DICOM {dicom_spacing[2]:.4f} vs NIfTI {nifti_spacing[2]:.4f}")
            return False, nifti_shape, nifti_spacing
             
    except Exception as e:
        print(f"Error reading {dicom_dir.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(
                    prog='Spatial Metadata Verifier',
                    description='Verify if NIfTI spatial metadata matches original DICOMs. Checks dataset dimensional uniformity.',
                    epilog='Provide input DICOM directory and input NIfTI directory.')
    parser.add_argument("dicom_dir")
    parser.add_argument("nifti_dir")
    args = parser.parse_args()
        
    dicom_root = Path(args.dicom_dir).resolve()
    nifti_root = Path(args.nifti_dir).resolve()

    if not dicom_root.is_dir() or not nifti_root.is_dir():
        raise NotADirectoryError("Both arguments must be directories.")

    dicom_dirs = find_dicom_directories(dicom_root)
    if not dicom_dirs:
        raise FileNotFoundError(f"No DICOM directories found in {dicom_root}")
        
    total_dirs = len(dicom_dirs)
    print(f"Starting verification of {total_dirs} directories...")
    
    success_count = 0
    missing_count = 0
    
    nifti_shapes = set()
    nifti_spacings = set()

    for i, dicom_dir in enumerate(dicom_dirs, start=1):
        relative_path = dicom_dir.relative_to(dicom_root)
        safe_name = "@".join(relative_path.parts)
        expected_nifti_name = f"{safe_name}.nii.gz"
        nifti_path = nifti_root / expected_nifti_name
        
        print(f"[{i}/{total_dirs}] Verifying: {relative_path} -> {expected_nifti_name}")
        
        if not nifti_path.exists():
            print(f"  Warning: Missing NIfTI file for {safe_name}")
            missing_count += 1
            continue
            
        result = verify_single_pair(dicom_dir, nifti_path)
        if result is not None:
            is_match, shape, spacing = result
            if is_match:
                success_count += 1
            nifti_shapes.add(shape)
            nifti_spacings.add((round(float(spacing[0]), 3), round(float(spacing[1]), 3), round(float(spacing[2]), 3)))

    processed = total_dirs - missing_count
    print(f"Finished: {success_count} success, {processed - success_count} failed out of {processed}")
    if missing_count > 0:
        print(f"Ignored {missing_count} directory(ies) due to missing NIfTI files.")

    print("-" * 60)
    print("Dimensional Uniformity Check:")
    if processed > 0:
        if len(nifti_shapes) == 1:
            print(f"Shape check: OK. All NIfTI files have identical dimensions: {list(nifti_shapes)[0]}")
        else:
            print("Shape check: WARNING. Found varying dimensions across files:")
            for shape in sorted(nifti_shapes):
                print(f"  - {shape}")
            
        if len(nifti_spacings) == 1:
            print(f"Spacing check: OK. All NIfTI files have identical voxel resolutions: {list(nifti_spacings)[0]}")
        else:
            print("Spacing check: WARNING. Found varying voxel resolutions:")
            for spc in sorted(nifti_spacings):
                print(f"  - {spc}")

if __name__ == "__main__":
    main()
