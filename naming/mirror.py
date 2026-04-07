"""Mirror naming strategy implementation.

Recreates the original folder structure in the output."""
from pathlib import Path
from naming.base import NamingStrategy


class MirrorStrategy(NamingStrategy):
    """Keeps the same directory structure as the source.
    Example: patient_01/head/scan -> output/patient_01/head/scan.nii.gz"""

    def build_output_path(
        self, output_dir: Path, relative_path: Path, index: int) -> Path:
        target_dir = output_dir / relative_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / f"{relative_path.name}.nii.gz"

    def resolve_nifti_path(
        self, output_dir: Path, relative_path: Path) -> Path | None:
        return output_dir / relative_path.parent / f"{relative_path.name}.nii.gz"
