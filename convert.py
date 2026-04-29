import argparse
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import dicom2nifti
from tqdm import tqdm

from utils import find_dicom_directories, setup_logging, add_logger_args
from naming import get_strategy, available_strategies

SEPARATOR = "━" * 80
logger = logging.getLogger("convert")


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
        logger.error("Conversion failed for %s: %s", dicom_dir.name, e)
        return False

    return True


def main():
    strategies = available_strategies()
    default_jobs = 8

    parser = argparse.ArgumentParser(
        prog="convert",
        description=("Batch converter for DICOM directories to .nii.gz files. "
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
    parser.add_argument("-j", "--jobs", type=int, default=default_jobs,
        help=f"Number of parallel jobs for conversion (default: {default_jobs})"
    )
    add_logger_args(parser)
    args = parser.parse_args()

    setup_logging("convert", log_file=args.log_file, verbose=args.verbose)

    root_dir = Path(args.dir).resolve()
    save_dir = Path(args.save).resolve()

    if not root_dir.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {root_dir}")

    save_dir.mkdir(parents=True, exist_ok=True)

    dicom_dirs = find_dicom_directories(root_dir)
    if not dicom_dirs:
        raise FileNotFoundError(f"No DICOM directories found in {root_dir}")

    if args.jobs < 1:
        raise ValueError("There must be at least 1 job")

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

    jobs: list[tuple[Path, Path, Path]] = []
    for i, dicom_dir in enumerate(dicom_dirs, start=1):
        relative_path = dicom_dir.relative_to(root_dir)
        if relative_path == Path("."):
            relative_path = Path(dicom_dir.name)
        output_file = strategy.build_output_path(save_dir, relative_path, i)
        jobs.append((dicom_dir, relative_path, output_file))

    logger.info(SEPARATOR)
    logger.info("DICOM -> NIfTI Conversion")
    logger.info(SEPARATOR)
    logger.info("Source:    %s", root_dir)
    logger.info("Output:    %s", save_dir)
    logger.info("Mode:      %s", args.mode)
    logger.info("Jobs:      %s", args.jobs)
    logger.info("Items:     %s", total)
    logger.info(SEPARATOR)

    if args.jobs == 1:
        pbar = tqdm(jobs, disable=args.quiet, unit="series", desc="Converting")
        for dicom_dir, relative_path, output_file in pbar:
            pbar.set_postfix_str(f"{relative_path}")

            if convert_single(dicom_dir, output_file):
                successes += 1
                logger.debug("Converted: %s", relative_path)
            else:
                failures += 1
                failed_dirs.append(str(relative_path))
                logger.warning("Failed: %s", relative_path)
    else:
        pbar = tqdm(disable=args.quiet, total=total, unit="series", desc="Converting")
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            future2path = {
                executor.submit(convert_single, dicom_dir, output_file): relative_path
                for dicom_dir, relative_path, output_file in jobs
            }

            for future in as_completed(future2path.keys()):
                relative_path = future2path[future]
                pbar.set_postfix_str(f"{relative_path}")

                try:
                    result = future.result()
                except Exception as e:
                    logger.error("Error: %s: %s", relative_path, e)
                    result = False

                if result:
                    successes += 1
                    logger.debug("Converted: %s", relative_path)
                else:
                    failures += 1
                    failed_dirs.append(str(relative_path))
                    logger.warning("Failed: %s", relative_path)

                pbar.update(1)

    strategy.on_conversion_complete(save_dir)

    # Summary
    logger.info(SEPARATOR)
    logger.info("Conversion Summary")
    logger.info(SEPARATOR)
    logger.info("Successful:  %s/%s", successes, total)
    if failures > 0:
        logger.warning("Failed:      %s/%s", failures, total)
        for name in failed_dirs:
            logger.warning("    - %s", name)
    if total > 0:
        logger.info("Success rate:  %.1f%%", (successes / total) * 100)
    logger.info(SEPARATOR)

if __name__ == "__main__":
    main()
