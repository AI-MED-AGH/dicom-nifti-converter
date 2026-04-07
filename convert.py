"""Automated DICOM to NIfTI converter with configurable output structure.

Finds DICOM series recursively, converts each one to .nii.gz using dicom2nifti
with RAS reorientation, and places output files according to the chosen
naming strategy.
"""
import argparse
from pathlib import Path
import dicom2nifti
from tqdm import tqdm

from utils import find_dicom_directories
from naming import get_strategy, available_strategies


def convert_single(dicom_dir: Path, output_path: Path) -> bool:
    """Converts a single DICOM series to a NIfTI file with RAS reorientation.

    Args:
        dicom_dir: The directory containing the source .dcm files.
        output_path: The absolute path where the .nii.gz file should be saved.

    Returns:
        True if the conversion was successful, False otherwise.
    """
    if not dicom_dir.is_dir():
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        dicom2nifti.dicom_series_to_nifti(str(dicom_dir), str(output_path), reorient_nifti=True)
    except Exception as e:
        tqdm.write(f"Error: {dicom_dir.name}: {e}")
        return False

    return True


def main():
    strategies = available_strategies()

    parser = argparse.ArgumentParser(
        prog="convert",
        description=("Mass converter for DICOM directories to .nii.gz files. "
            "Supports multiple output directory structures via --mode."),
        epilog="Provide input DICOM directory and output save directory.",
    )
    parser.add_argument("dir", help="Root directory containing DICOM series")
    parser.add_argument("-s", "--save", required=True, help="Output directory for NIfTI files")
    parser.add_argument("--mode", choices=strategies, default="flat", 
        help=f"Output structure mode (default: flat). Available: {strategies}")
    parser.add_argument("--sep", default="@", 
        help="Separator for compatible naming strategies (default: '@')")
    parser.add_argument("--prefix", default="vol",
        help="Base filename prefix for compatible naming strategies (default: 'vol')",
    )
    args = parser.parse_args()

    root_dir = Path(args.dir).resolve()
    save_dir = Path(args.save).resolve()

    if not root_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {root_dir}")

    save_dir.mkdir(parents=True, exist_ok=True)

    dicom_dirs = find_dicom_directories(root_dir)
    if not dicom_dirs:
        raise FileNotFoundError(f"No DICOM directories found in {root_dir}")

    strategy_kwargs = {}
    if args.mode == "flat":
        strategy_kwargs["sep"] = args.sep
    elif args.mode == "map":
        strategy_kwargs["prefix"] = args.prefix
    strategy = get_strategy(args.mode, **strategy_kwargs)

    total = len(dicom_dirs)
    successes = 0
    failures = 0
    failed_dirs: list[str] = []

    print(f"\n{'-' * 60}")
    print("DICOM → NIfTI Conversion")
    print(f"{'-' * 60}")
    print(f"Source:    {root_dir}")
    print(f"Output:    {save_dir}")
    print(f"Mode:      {args.mode}")
    print(f"Items:     {total}")
    print(f"{'-' * 60}\n")

    progress = tqdm(enumerate(dicom_dirs, start=1), total=total, unit="series", desc="Converting")

    for i, dicom_dir in progress:
        relative_path = dicom_dir.relative_to(root_dir)
        if relative_path == Path("."):
            relative_path = Path(dicom_dir.name)
        output_file = strategy.build_output_path(save_dir, relative_path, i)

        progress.set_postfix_str(f"{relative_path}")

        if convert_single(dicom_dir, output_file):
            successes += 1
        else:
            failures += 1
            failed_dirs.append(str(relative_path))

    strategy.on_conversion_complete(save_dir)

    #Summary
    print(f"\n{'-' * 60}")
    print("Conversion Summary")
    print(f"{'-' * 60}")
    print(f"Successful:  {successes}/{total}")
    if failures > 0:
        print(f"Failed:      {failures}/{total}")
        for name in failed_dirs:
            print(f"    - {name}")
    print(f"Success rate:  {successes / total:.1%}" if total > 0 else "")

if __name__ == "__main__":
    main()
