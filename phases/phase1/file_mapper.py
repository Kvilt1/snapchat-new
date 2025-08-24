"""
Phase 1 T1.2: File Mapping Index Module.
Creates mappings between media IDs and physical files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from .media_id_extractor import extract_media_id_from_filename

logger = logging.getLogger(__name__)


def create_media_index(media_dir: Path, use_parallel: bool = False, max_workers: int = 4) -> Dict[str, str]:
    """
    Build a mapping of Media ID to filename.
    Adapted from snapchat_merger/media_mapper.py:68-121
    
    Args:
        media_dir: The directory containing media files
        use_parallel: Whether to use parallel processing for large directories
        max_workers: Number of parallel workers (if use_parallel is True)
        
    Returns:
        A dictionary mapping Media IDs to filenames
    """
    if not media_dir.exists():
        logger.warning(f"Media directory does not exist: {media_dir}")
        return {}
    
    # Get all non-hidden files
    filenames = [f.name for f in media_dir.iterdir() 
                 if f.is_file() and not f.name.startswith('.')]
    
    logger.info(f"Found {len(filenames)} files in {media_dir}")
    
    # Use parallel processing for large directories (>1000 files)
    if use_parallel and len(filenames) > 1000:
        media_map = {}
        lock = threading.Lock()
        
        def process_file(filename: str) -> Optional[Tuple[str, str]]:
            media_id = extract_media_id_from_filename(filename)
            return (media_id, filename) if media_id else None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_file, f) for f in filenames]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    media_id, filename = result
                    with lock:
                        media_map[media_id] = filename
        
        logger.info(f"Mapped {len(media_map)} Media IDs using parallel processing")
        return media_map
    else:
        # Sequential processing for smaller directories
        media_map = {}
        for filename in filenames:
            media_id = extract_media_id_from_filename(filename)
            if media_id:
                media_map[media_id] = filename
        
        logger.info(f"Mapped {len(media_map)} Media IDs using sequential processing")
        return media_map