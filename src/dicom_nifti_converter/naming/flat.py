from pathlib import Path
from .base import NamingStrategy


class FlatStrategy(NamingStrategy):
    """Joins folder names with a separator to make unique flat filenames.
    Example with sep='@': patient_01/head/scan -> patient_01@head@scan.nii.gz"""

    def __init__(self, sep: str = "@"):
        self.sep = sep

    def build_output_path(
        self, output_dir: Path, relative_path: Path, index: int) -> Path:
        safe_name = self.sep.join(relative_path.parts)
        return output_dir / f"{safe_name}.nii.gz"

    def resolve_nifti_path(
        self, output_dir: Path, relative_path: Path) -> Path | None:
        safe_name = self.sep.join(relative_path.parts)
        return output_dir / f"{safe_name}.nii.gz"