import json
from pathlib import Path

from naming.base import NamingStrategy


class MapStrategy(NamingStrategy):
    """Uses a prefix and sequential index for filenames, saving a JSON mapping.
    Example with prefix='vol': patient_01/head/scan -> vol_31.nii.gz"""

    def __init__(self, prefix: str = "vol"):
        self.prefix = prefix
        self._mapping: dict[str, str] = {}
        self._reverse_map: dict[str, str] = {}

    def build_output_path(self, output_dir: Path, relative_path: Path, index: int) -> Path:
        vol_name = f"{self.prefix}_{index}.nii.gz"
        self._mapping[vol_name] = relative_path.as_posix()
        return output_dir / vol_name

    def resolve_nifti_path(self, output_dir: Path, relative_path: Path) -> Path | None:
        nifti_name = self._reverse_map.get(relative_path.as_posix())
        if nifti_name is None:
            return None
        return output_dir / nifti_name

    def load_map(self, output_dir: Path) -> None:
        """Restores the naming registry from disk to enable file lookups.

        Args:
            output_dir: The directory containing the 'dataset_map.json' file.

        Raises:
            FileNotFoundError: If the mapping file does not exist.
        """
        map_file = output_dir / "dataset_map.json"
        if not map_file.exists():
            raise FileNotFoundError(f"Missing dataset_map.json in {output_dir}")
        with open(map_file, "r", encoding="utf-8") as f:
            self._mapping = json.load(f)
        self._reverse_map = {v: k for k, v in self._mapping.items()}

    def on_conversion_complete(self, output_dir: Path) -> None:
        """Saves the naming registry to a JSON file.

        Args:
            output_dir: The directory where 'dataset_map.json' will be saved.
        """
        if self._mapping:
            map_path = output_dir / "dataset_map.json"
            with open(map_path, "w", encoding="utf-8") as f:
                json.dump(self._mapping, f, indent=4)
            print(f"Saved dataset mapping to: {map_path.name}")
