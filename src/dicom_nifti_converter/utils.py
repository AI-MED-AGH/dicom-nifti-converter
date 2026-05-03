import logging
import sys
from pathlib import Path

def find_dicom_directories(root_dir: Path) -> list[Path]:
    """Recursively scans a directory for subdirectories containing DICOM files.

    Args:
        root_dir: The root directory to start the search from.

    Returns:
        A list of Path objects representing directories that contain .dcm files.
    """
    if next(root_dir.glob("*.dcm"), None) is not None:
        return [root_dir]

    dicom_dirs = []
    for path in sorted(root_dir.iterdir()):
        if not path.is_dir() or path.name.startswith(".") or path.name in {"__pycache__"}:
            continue

        if next(path.glob("*.dcm"), None) is not None:
            dicom_dirs.append(path)
        else:
            dicom_dirs.extend(find_dicom_directories(path))
    return dicom_dirs


def setup_logging(name: str, log_file: str | None = None, verbose: bool = False) -> logging.Logger:
    """Configures and returns a logger with console and optional file output.
    The console handler uses a compact format while the file handler includes
    timestamps and log levels.

    Args:
        name: Logger name.
        log_file: Optional path to a log file. When provided, all messages at
            DEBUG level and above are written to this file.
        verbose: If True, the console handler uses DEBUG level, otherwise INFO.

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_fmt = logging.Formatter("%(message)s")
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger


def add_logger_args(parser) -> None:
    """Adds --log-file, --verbose, and --quiet flags to an ArgumentParser.

    Args:
        parser: An argparse.ArgumentParser instance to extend.
    """
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to a log file. When set, all messages are also written to this file.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG-level) console output.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        default=False,
        help="Suppress progress bar.",
    )
