"""Utilities for safe ZIP file extraction with zip-slip vulnerability protection."""

from pathlib import Path
from zipfile import ZipFile


def safe_extract_zip(zip_file: ZipFile, target_dir: Path) -> None:
    """
    Extract all members from a ZIP file safely, preventing zip-slip attacks.
    
    Validates that no member paths attempt to escape the target directory
    using path traversal techniques (e.g., ../../).
    
    Args:
        zip_file: An open ZipFile object.
        target_dir: The destination directory for extraction.
    
    Raises:
        ValueError: If any member path would escape the target directory.
    
    Example:
        >>> with ZipFile(path_to_zip, 'r') as zf:
        ...     safe_extract_zip(zf, Path('/tmp/extract'))
    """
    target_dir = Path(target_dir).resolve()
    
    for member in zip_file.namelist():
        # Resolve the member path relative to target directory
        member_path = (target_dir / member).resolve()
        
        # Verify the resolved path is within target_dir
        try:
            member_path.relative_to(target_dir)
        except ValueError:
            raise ValueError(
                f"Zip-slip vulnerability detected: member '{member}' "
                f"attempts to escape target directory"
            )
        
        # Extract the member
        zip_file.extract(member, target_dir)
