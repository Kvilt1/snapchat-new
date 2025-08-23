"""
Overlay merger module for combining media files with overlay images.
Adapted from snapchat_merger/media_preprocessor.py
"""

import os
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


def get_media_dimensions(media_path: str) -> Tuple[int, int]:
    """Extract media dimensions using ffmpeg probe (works for both video and images)."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json', media_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)
        
        if data['streams']:
            stream = data['streams'][0]
            return int(stream['width']), int(stream['height'])
        else:
            raise ValueError(f"No video stream found in {media_path}")
    except Exception as e:
        print(f"Error getting media dimensions: {e}")
        raise


def get_media_info(media_path: str) -> Dict[str, Any]:
    """Get comprehensive media info with a single ffprobe call."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_streams',
            '-show_format',
            '-of', 'json', media_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)
        
        # Extract dimensions from video stream
        width, height = None, None
        has_audio = False
        
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and width is None:
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
            elif stream.get('codec_type') == 'audio':
                has_audio = True
        
        return {
            'width': width,
            'height': height,
            'has_audio': has_audio,
            'format': data.get('format', {})
        }
    except Exception as e:
        print(f"Error getting media info: {e}")
        return {'width': None, 'height': None, 'has_audio': False, 'format': {}}


def get_media_type(file_path: str) -> str:
    """
    Determine if file is video or image based on extension.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        'video' or 'image'
    """
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
    ext = Path(file_path).suffix.lower()
    return 'video' if ext in video_extensions else 'image'


def overlay_webp_on_media(media_path: str, overlay_path: str, output_path: str) -> None:
    """Overlay a WebP image with transparency onto a video or image."""
    # Get all media info in one call
    media_info = get_media_info(media_path)
    width = media_info['width']
    height = media_info['height']
    has_audio = media_info['has_audio']
    
    if width is None or height is None:
        raise ValueError(f"Could not get dimensions for {media_path}")
    
    media_type = get_media_type(media_path)
    is_video = (media_type == "video")
    
    try:
        # Build base ffmpeg command
        cmd = [
            'ffmpeg', '-i', media_path, '-i', overlay_path,
            '-filter_complex',
            f'[1:v]alphaextract[a];[1:v][a]alphamerge,scale={width}:{height}[overlay];[0:v][overlay]overlay=0:0',
        ]
        
        # Add audio handling only if the video has audio
        if is_video and has_audio:
            cmd.extend(['-c:a', 'copy'])
        
        # Add metadata copying
        cmd.extend(['-map_metadata', '0'])
        
        # Only add audio metadata mapping if audio exists
        if is_video and has_audio:
            cmd.extend(['-map_metadata:s:a', '0:s:a'])
        
        # Add output file
        cmd.extend(['-y', output_path])
        
        subprocess.run(cmd, capture_output=True, check=True)
        print(f"Overlay completed: {os.path.basename(output_path)}")
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"FFmpeg error: {error_msg}")
        raise
    except Exception as e:
        print(f"Error during overlay: {e}")
        raise


def generate_output_filename(media_path: str, overlay_path: str, media_type: str) -> str:
    """Generate output filename - use original media filename."""
    # Simply return the media filename
    return os.path.basename(media_path)


def process_overlay_pair(media_dir: Path, date: str, media_file: str, overlay_file: str) -> Tuple[bool, Optional[str]]:
    """Process a single overlay pair.
    
    Returns
    -------
    Tuple[bool, Optional[str]]
        (success, error_message)
    """
    media_path = str(media_dir / media_file)
    overlay_path = str(media_dir / overlay_file)
    
    try:
        # Determine media type
        media_type = get_media_type(media_path)
        
        # Generate output filename (will be same as media filename)
        output_filename = generate_output_filename(media_path, overlay_path, media_type)
        
        # For in-place merging, we need a temporary output file
        temp_output_path = str(media_dir / f"temp_{output_filename}")
        final_output_path = str(media_dir / output_filename)
        
        # Merge to temporary file first
        overlay_webp_on_media(media_path, overlay_path, temp_output_path)
        
        # Delete original files
        os.remove(media_path)
        os.remove(overlay_path)
        
        # Move temp file to final location
        os.rename(temp_output_path, final_output_path)
        
        return True, None
        
    except Exception as e:
        return False, str(e)


def process_all_overlay_pairs(
    media_dir: Path, 
    use_parallel: bool = True, 
    max_workers: int = 4
) -> Dict[str, Any]:
    """
    Find and merge all overlay-media pairs in directory.
    Adapted from snapchat_merger/media_preprocessor.py:306-427
    
    Args:
        media_dir: Directory containing media files
        use_parallel: Whether to use parallel processing
        max_workers: Number of parallel workers
        
    Returns:
        Dictionary with statistics about the merging process
    """
    # Import detect_overlay_pairs directly to avoid circular import
    from pathlib import Path
    from collections import defaultdict
    import re
    
    # Inline the detect_overlay_pairs function to avoid circular import
    files_by_date = defaultdict(lambda: {"media": [], "overlay": []})
    
    for file in media_dir.iterdir():
        if file.is_file():
            # Extract date from filename (format: YYYY-MM-DD_...)
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})_', file.name)
            if date_match:
                date = date_match.group(1)
                
                # Categorize by type (excluding thumbnails)
                if '_media~' in file.name and 'thumbnail' not in file.name.lower():
                    files_by_date[date]["media"].append(file)
                elif '_overlay~' in file.name:
                    files_by_date[date]["overlay"].append(file)
    
    # Find single pairs per date
    pairs = []
    for date, files in files_by_date.items():
        if len(files["media"]) == 1 and len(files["overlay"]) == 1:
            pairs.append((files["media"][0], files["overlay"][0]))
    
    stats = {
        'total_pairs': len(pairs),
        'merged': 0,
        'failed': 0,
        'errors': []
    }
    
    if not pairs:
        logger.info("No overlay pairs found to merge")
        return stats
    
    logger.info(f"Found {len(pairs)} overlay pairs to merge")
    
    # Process pairs
    if use_parallel and len(pairs) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all merge tasks
            futures = {}
            for media_file, overlay_file in pairs:
                # Extract date from filename
                date = media_file.name.split('_')[0] if '_' in media_file.name else "unknown"
                future = executor.submit(
                    process_overlay_pair,
                    media_dir, date, media_file.name, overlay_file.name
                )
                futures[future] = (media_file, overlay_file)
            
            # Collect results
            for future in as_completed(futures):
                media_file, overlay_file = futures[future]
                try:
                    success, error_msg = future.result()
                    if success:
                        stats['merged'] += 1
                    else:
                        stats['failed'] += 1
                        if error_msg:
                            stats['errors'].append(error_msg)
                except Exception as e:
                    stats['failed'] += 1
                    error_msg = f"Exception processing {media_file.name}: {str(e)}"
                    stats['errors'].append(error_msg)
                    logger.error(error_msg)
    else:
        # Sequential processing
        for media_file, overlay_file in pairs:
            date = media_file.name.split('_')[0] if '_' in media_file.name else "unknown"
            success, error_msg = process_overlay_pair(
                media_dir, date, media_file.name, overlay_file.name
            )
            if success:
                stats['merged'] += 1
            else:
                stats['failed'] += 1
                if error_msg:
                    stats['errors'].append(error_msg)
    
    # Log summary
    logger.info(f"Overlay merging complete: {stats['merged']}/{stats['total_pairs']} successful")
    if stats['failed'] > 0:
        logger.warning(f"{stats['failed']} pairs failed to merge")
    
    return stats