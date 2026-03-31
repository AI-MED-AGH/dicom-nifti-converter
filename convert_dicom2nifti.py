"""
This script automates the mass conversion of raw DICOM medical scans into the 3D NIfTI format.
It features:
1. Recursive searching to safely find hidden DICOM patients in nested folder structures.
2. Automatic generation of 3D NIfTI volumes using the `dicom2nifti` library.
3. Forced RAS orientation (`reorient_nifti=True`) to standardize the affine matrix.
"""
import argparse
import sys
from pathlib import Path
import dicom2nifti

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

def convert_dicom_to_nifti(dicom_dir: Path, output_path: Path) -> bool:
    if not dicom_dir.is_dir():
        print(f"Directory does not exist: {dicom_dir}")
        return False

    try:
        dicom2nifti.dicom_series_to_nifti(str(dicom_dir), str(output_path), reorient_nifti=True)
    except Exception as e:
        print(f"Error converting {dicom_dir.name}: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
                    prog='DICOM to NIfTI converter',
                    description='Mass converter for DICOM directories to .nii.gz files',
                    epilog='Provide input directory and output save directory')
    parser.add_argument("dir")
    parser.add_argument("-s", "--save", required=True)
    args = parser.parse_args()

    root_dir = Path(args.dir).resolve()
    save_dir = Path(args.save).resolve()

    if not root_dir.is_dir():
        print(f"Error: Input directory does not exist: {root_dir}")
        sys.exit(1)

    save_dir.mkdir(parents=True, exist_ok=True)
    
    dicom_dirs = find_dicom_directories(root_dir)
    if not dicom_dirs:
        print(f"Error: No DICOM directories found in {root_dir}")
        sys.exit(1)

    total_dirs = len(dicom_dirs)
    successes = 0
    failures = 0

    print(f"Starting conversion of {total_dirs} directories...")

    for i, dicom_dir in enumerate(dicom_dirs, start=1):
        relative_path = dicom_dir.relative_to(root_dir)
        safe_name = "_".join(relative_path.parts)
        output_file = save_dir / f"{safe_name}.nii.gz"
        
        print(f"[{i}/{total_dirs}] Converting: {relative_path} -> {output_file.name}")
        
        if convert_dicom_to_nifti(dicom_dir, output_file):
            successes += 1
        else:
            failures += 1

    print("-" * 60)
    print(f"Finished: {successes} success, {failures} failed out of {total_dirs}")
    
if __name__ == "__main__":
    main()
