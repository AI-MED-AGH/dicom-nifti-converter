from abc import ABC, abstractmethod
from pathlib import Path

class NamingStrategy(ABC):
    """Base class defining the rules for naming and locating output files."""

    @abstractmethod
    def build_output_path(
        self, output_dir: Path, relative_path: Path, index: int
    ) -> Path:
        """Determines the destination path for a converted NIfTI file.

        Args:
            output_dir: The root directory where NIfTI files should be stored.
            relative_path: The relative path of the DICOM series from the source root.
            index: The sequential number of the series being processed.

        Returns:
            The final absolute path where the .nii.gz file will be saved.
        """

    @abstractmethod
    def resolve_nifti_path(
        self, output_dir: Path, relative_path: Path) -> Path | None:
        """Resolves the expected path of a NIfTI file during validation.

        Args:
            output_dir: The root directory where NIfTI files are stored.
            relative_path: The relative path of the DICOM series from the source root.

        Returns:
            The absolute path to the expected .nii.gz file, or None if the mapping
            cannot be resolved.
        """

    def on_conversion_complete(self, output_dir: Path) -> None:
        """Called once after all files are converted.

        Implement this method if your strategy needs to save extra data, like JSON mappings.

        Args:
            output_dir: The directory where NIfTI files should be stored.
        """
