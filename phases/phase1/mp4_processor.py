"""
Phase 1 T1.3: MP4 Processing Module.
Handles MP4 timestamp extraction and processing.
"""

import struct
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants from original config
ATOM_HEADER_SIZE = 8
QUICKTIME_EPOCH_ADJUSTER = 2082844800  # Seconds between 1904 and 1970


def parse_mp4_timestamp_binary(mp4_path: Path) -> Optional[int]:
    """
    Extract creation time by parsing MP4 atoms directly.
    Adapted from snapchat_merger/audio_timestamp_matcher.py:23-102
    
    This is much faster than using ffprobe subprocess as it only reads
    the necessary bytes from the file header.
    
    Args:
        mp4_path: The path to the MP4 file
        
    Returns:
        The creation timestamp in milliseconds since Unix epoch, or None if extraction fails
    """
    try:
        with open(mp4_path, "rb") as f:
            # Search for moov atom
            while True:
                atom_header = f.read(ATOM_HEADER_SIZE)
                if len(atom_header) < ATOM_HEADER_SIZE:
                    return None
                    
                atom_type = atom_header[4:8]
                if atom_type == b'moov':
                    break  # Found moov atom
                    
                # Get atom size and skip to next atom
                atom_size = struct.unpack('>I', atom_header[0:4])[0]
                if atom_size == 0:  # Atom extends to end of file
                    return None
                elif atom_size == 1:  # 64-bit atom size
                    extended_size = struct.unpack('>Q', f.read(8))[0]
                    f.seek(extended_size - 16, 1)
                else:
                    f.seek(atom_size - 8, 1)
            
            # Found 'moov', now look for 'mvhd' inside it
            atom_header = f.read(ATOM_HEADER_SIZE)
            if atom_header[4:8] == b'cmov':
                # Compressed movie atom, can't parse
                return None
            elif atom_header[4:8] != b'mvhd':
                # Expected mvhd to be first atom in moov
                return None
            
            # Read mvhd version
            version = f.read(1)[0]
            f.seek(3, 1)  # Skip flags
            
            # Read creation time (32-bit for v0, 64-bit for v1)
            if version == 0:
                creation_time = struct.unpack('>I', f.read(4))[0]
            else:
                creation_time = struct.unpack('>Q', f.read(8))[0]
                
            if creation_time > 0:
                # Convert from QuickTime epoch to Unix epoch
                unix_timestamp = creation_time - QUICKTIME_EPOCH_ADJUSTER
                # Return milliseconds for consistency with message timestamps
                return unix_timestamp * 1000
                
        return None
        
    except (IOError, OSError, struct.error) as e:
        logger.debug(f"Error parsing MP4 {mp4_path}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error parsing MP4 {mp4_path}: {e}")
        return None


def parse_mp4_timestamp_ffprobe(mp4_path: Path) -> Optional[int]:
    """
    Extract creation time from the audio stream using ffprobe.
    Adapted from snapchat_merger/audio_timestamp_matcher.py:104-151
    
    This is the fallback method when direct parsing fails.
    
    Args:
        mp4_path: The path to the MP4 file
        
    Returns:
        The creation timestamp in milliseconds since Unix epoch, or None if extraction fails
    """
    try:
        # Run ffprobe to get stream information
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            str(mp4_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
        data = json.loads(result.stdout)
        
        # Look for audio stream (usually stream 0)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'audio':
                tags = stream.get('tags', {})
                creation_time = tags.get('creation_time')
                
                if creation_time:
                    # Parse ISO format timestamp
                    # Format: "2025-07-28T15:28:18.000000Z"
                    dt = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                    # Convert to milliseconds since Unix epoch
                    return int(dt.timestamp() * 1000)
        
        return None
        
    except subprocess.CalledProcessError as e:
        logger.debug(f"ffprobe failed for {mp4_path}: {e}")
        return None
    except subprocess.TimeoutExpired:
        logger.debug(f"ffprobe timeout for {mp4_path}")
        return None
    except json.JSONDecodeError as e:
        logger.debug(f"Failed to parse ffprobe output for {mp4_path}: {e}")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error with ffprobe for {mp4_path}: {e}")
        return None


def extract_mp4_timestamp(mp4_path: Path, use_ffprobe_fallback: bool = True) -> Optional[int]:
    """
    Extract MP4 creation timestamp with optional ffprobe fallback.
    
    Args:
        mp4_path: Path to the MP4 file
        use_ffprobe_fallback: Whether to fall back to ffprobe if binary parsing fails
        
    Returns:
        Timestamp in milliseconds since Unix epoch, or None if extraction fails
    """
    # Try direct binary parsing first (faster)
    timestamp = parse_mp4_timestamp_binary(mp4_path)
    
    # Fall back to ffprobe if needed
    if timestamp is None and use_ffprobe_fallback:
        logger.debug(f"Binary parsing failed for {mp4_path}, trying ffprobe")
        timestamp = parse_mp4_timestamp_ffprobe(mp4_path)
    
    return timestamp