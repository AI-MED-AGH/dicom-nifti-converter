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
