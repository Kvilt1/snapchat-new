"""
Configuration management for Snapchat Merger V2
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Config:
    """Main configuration class for the merger."""
    
    # Paths (will be set from args or defaults)
    data_dir: Path = None
    output_dir: Path = None
    
    # Processing
    parallel_workers: int = 4
    batch_size: int = 100
    timestamp_threshold_seconds: int = 10
    
    # File patterns
    exclude_patterns: List[str] = field(default_factory=lambda: ["thumbnail~"])
    media_patterns: List[str] = field(default_factory=lambda: [
        "b~",
        "media~", 
        "overlay~",
        "media~zip-"
    ])
    
    # MP4 parsing constants
    ATOM_HEADER_SIZE: int = 8
    QUICKTIME_EPOCH_ADJUSTER: int = 2082844800  # Seconds between Unix and QuickTime epochs
    
    # Media processing
    overlay_quality: int = 95
    max_dimension: int = 4096
    
    # Validation
    max_file_size_mb: int = 500
    gc_collect_threshold: int = 100
    
    @classmethod
    def get_default_paths(cls) -> tuple[Path, Path]:
        """Get default input and output paths relative to the project."""
        # Get the snapchat-new directory (parent of config.py)
        project_dir = Path(__file__).parent
        return project_dir / "input", project_dir / "output"
    
    @classmethod
    def from_args(cls, args) -> "Config":
        """Create config from command-line arguments."""
        # Use args.input if available (from --input flag)
        data_dir = getattr(args, 'input', None)
        if data_dir is None:
            data_dir, _ = cls.get_default_paths()
        
        # Use args.output if available
        output_dir = getattr(args, 'output', None)
        if output_dir is None:
            _, output_dir = cls.get_default_paths()
        
        return cls(
            data_dir=data_dir,
            output_dir=output_dir,
            parallel_workers=getattr(args, 'workers', 4),
            timestamp_threshold_seconds=getattr(args, 'timestamp_threshold', 10)
        )