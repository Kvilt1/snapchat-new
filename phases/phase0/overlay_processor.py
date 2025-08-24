"""
Phase 0 Overlay Processor Module.
Handles detection and merging of overlay-media pairs.
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


def detect_overlay_pairs(media_dir: Path) -> List[Tuple[Path, Path]]:
    """
    Detect media~overlay pairs for the same date.
    
    Args:
        media_dir: Directory containing media files
        
    Returns:
        List of (media_file, overlay_file) tuples
    """
    files_by_date = defaultdict(lambda: {"media": [], "overlay": []})
    
    for file_path in media_dir.iterdir():
        if not file_path.is_file():
            continue
        
        # Extract date from filename
        parts = file_path.name.split('_', 1)
        if len(parts) >= 2:
            date = parts[0]  # YYYY-MM-DD format
            
            if '_media~' in file_path.name and '_overlay~' not in file_path.name:
                files_by_date[date]["media"].append(file_path)
            elif '_overlay~' in file_path.name:
                files_by_date[date]["overlay"].append(file_path)
    
    # Find single pairs per date
    pairs = []
    for date, files in files_by_date.items():
        if len(files["media"]) == 1 and len(files["overlay"]) == 1:
            pairs.append((files["media"][0], files["overlay"][0]))
            logger.debug(f"Found overlay pair for {date}")
    
    return pairs


def merge_overlay_pairs(temp_dir: Path, max_workers: int = 4) -> int:
    """
    Merge overlay-media pairs using ffmpeg.
    
    Args:
        temp_dir: Temporary media directory
        max_workers: Number of parallel workers
        
    Returns:
        Number of pairs successfully merged
    """
    try:
        # Import with absolute path for the test script
        module_path = Path(__file__).parent.parent.parent
        if str(module_path) not in sys.path:
            sys.path.insert(0, str(module_path))
        
        from core.overlay_merger import process_all_overlay_pairs
        
        # Process all overlay pairs with ffmpeg
        stats = process_all_overlay_pairs(
            media_dir=temp_dir,
            use_parallel=True,
            max_workers=max_workers
        )
        
        # Log statistics
        if stats['total_pairs'] > 0:
            logger.info(f"Overlay merging: {stats['merged']}/{stats['total_pairs']} successful")
            if stats['failed'] > 0:
                logger.warning(f"Failed to merge {stats['failed']} overlay pairs")
                for error in stats['errors'][:5]:  # Log first 5 errors
                    logger.error(f"  - {error}")
        
        return stats['merged']
        
    except ImportError as e:
        logger.warning(f"Overlay merger module not available: {e}")
        logger.info("Falling back to detection-only mode")
        # Fallback to just detecting pairs
        pairs = detect_overlay_pairs(temp_dir)
        for media_file, overlay_file in pairs:
            logger.info(f"Found overlay pair: {media_file.name} + {overlay_file.name}")
        return 0
    except Exception as e:
        logger.error(f"Error during overlay merging: {e}")
        return 0