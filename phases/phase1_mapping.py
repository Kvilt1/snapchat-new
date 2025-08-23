"""
Phase 1: Media Mapping
Extracts media IDs from messages and maps them to physical files.
"""

import re
import logging
import struct
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
from collections import defaultdict
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class Phase1Stats:
    """Statistics for Phase 1 processing."""
    
    def __init__(self):
        self.total_media_ids = 0
        self.ids_mapped = 0
        self.ids_unmapped = 0
        self.mp4s_processed = 0
        self.mp4s_matched = 0
        self.unique_ids = 0
        self.pipe_separated_count = 0
        self.total_media_files = 0
        self.orphaned_files = 0
        self.duration = 0.0
        self.memory_used_mb = 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_media_ids": self.total_media_ids,
            "ids_mapped": self.ids_mapped,
            "ids_unmapped": self.ids_unmapped,
            "mp4s_processed": self.mp4s_processed,
            "mp4s_matched": self.mp4s_matched,
            "unique_ids": self.unique_ids,
            "pipe_separated_count": self.pipe_separated_count,
            "total_media_files": self.total_media_files,
            "orphaned_files": self.orphaned_files,
            "duration": self.duration,
            "memory_used_mb": self.memory_used_mb
        }


def load_all_conversations(conversations_dir: Path, groups_dir: Path) -> Dict[str, List[Dict]]:
    """Load all conversation files from Phase 0 output directories.
    
    Args:
        conversations_dir: Path to output/conversations/ directory
        groups_dir: Path to output/groups/ directory
        
    Returns:
        Dictionary mapping conversation IDs to message lists
    """
    logger.info(f"Loading conversations from {conversations_dir} and {groups_dir}")
    all_messages = {}
    
    # Process individual conversations
    if conversations_dir.exists():
        for conv_folder in conversations_dir.iterdir():
            if conv_folder.is_dir():
                conv_file = conv_folder / 'conversation.json'
                if conv_file.exists():
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Extract conversation ID from metadata
                    conv_id = data['conversation_metadata']['conversation_id']
                    all_messages[conv_id] = data.get('messages', [])
                    logger.debug(f"Loaded {len(data.get('messages', []))} messages from {conv_id}")
    
    # Process group conversations  
    if groups_dir.exists():
        for group_folder in groups_dir.iterdir():
            if group_folder.is_dir():
                group_file = group_folder / 'conversation.json'
                if group_file.exists():
                    with open(group_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Extract group ID from metadata
                    group_id = data['conversation_metadata']['conversation_id']
                    all_messages[group_id] = data.get('messages', [])
                    logger.debug(f"Loaded {len(data.get('messages', []))} messages from group {group_id}")
    
    logger.info(f"Loaded {len(all_messages)} total conversations")
    return all_messages


# ====================
# T1.1: Media ID Extraction
# ====================

def split_pipe_separated_ids(media_ids_str: str) -> List[str]:
    """
    Parse a Media IDs string which may contain multiple IDs separated by pipe.
    Adapted from snapchat_merger/media_mapper.py:123-142
    
    Args:
        media_ids_str: The Media IDs string, potentially containing multiple IDs 
                      separated by " | " (pipe with spaces).
        
    Returns:
        A list of individual Media IDs.
        
    Examples:
        >>> split_pipe_separated_ids("id1 | id2 | id3")
        ['id1', 'id2', 'id3']
        >>> split_pipe_separated_ids("single_id")
        ['single_id']
        >>> split_pipe_separated_ids("")
        []
    """
    if not media_ids_str:
        return []
    
    # Split by pipe separator WITH SPACES (as per actual data format)
    # The data uses " | " not just "|"
    ids = [id.strip() for id in media_ids_str.split(' | ') if id.strip()]
    return ids


def extract_media_ids_from_messages(messages: Dict[str, List[Dict[str, Any]]]) -> Tuple[Set[str], Dict[str, Any]]:
    """
    Extract all unique Media IDs from messages.
    
    Args:
        messages: Dictionary of conversations with message lists
        
    Returns:
        Tuple of (unique_media_ids set, statistics dict)
    """
    all_media_ids = set()
    stats = {
        'total_messages': 0,
        'messages_with_media': 0,
        'pipe_separated': 0,  # Changed key name to match what run_phase1 expects
        'total_ids': 0
    }
    
    for conversation_id, message_list in messages.items():
        for message in message_list:
            stats['total_messages'] += 1
            
            media_ids_field = message.get('Media IDs', '')
            if media_ids_field:
                stats['messages_with_media'] += 1
                
                # Parse the IDs
                ids = split_pipe_separated_ids(media_ids_field)
                
                if len(ids) > 1:
                    stats['pipe_separated'] += 1
                
                stats['total_ids'] += len(ids)
                all_media_ids.update(ids)
    
    logger.info(f"Extracted {len(all_media_ids)} unique Media IDs from {stats['total_messages']} messages")
    logger.info(f"Found {stats['pipe_separated']} messages with pipe-separated IDs")
    
    return all_media_ids, stats


# ====================
# T1.1.3: Extract Media ID from Filename
# ====================

def extract_media_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract the Media ID from a media filename.
    Adapted from snapchat_merger/media_mapper.py:18-65
    
    Media files can have patterns:
    - 2025-07-27_b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ.jpeg
    - 2025-07-27_media~28E0FFB8-5182-4D9D-92E1-DD941C881FC5.mp4
    - 2025-07-27_overlay~7E80A0BA-875C-49B0-8F4A-865EB6F8EC21.webp
    - 2025-07-30_media~zip-C63E6B4D-4DF6-4C2C-A331-A49E4F1C0109.mp4
    
    Args:
        filename: The media filename.
        
    Returns:
        The extracted Media ID if found, None otherwise.
    """
    # Exclude all thumbnail files
    if 'thumbnail~' in filename:
        return None
    
    # Look for b~ pattern in filename
    if 'b~' in filename:
        # Split by b~ and get everything after it
        parts = filename.split('b~', 1)
        if len(parts) > 1:
            # Get the ID part before the file extension
            id_with_ext = parts[1]
            # Remove the extension
            id_part = id_with_ext.rsplit('.', 1)[0]
            return f'b~{id_part}'
    
    # Special handling for media~zip pattern
    if '_media~zip-' in filename:
        match = re.search(r'media~zip-([A-F0-9\-]+)', filename)
        if match:
            return f'media~zip-{match.group(1)}'
    
    # Look for media~ or overlay~ pattern
    match = re.search(r'(?:media|overlay)~([A-F0-9\-]+)', filename)
    if match:
        prefix = 'media' if 'media~' in filename else 'overlay'
        return f'{prefix}~{match.group(1)}'
    
    return None


# ====================
# T1.2: File Mapping Index
# ====================

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
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
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


# ====================
# T1.3: MP4 Timestamp Extraction
# ====================

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


# ====================
# T1.4: Timestamp Matching
# ====================

def build_millisecond_index(messages: Dict[str, List[Dict[str, Any]]]) -> List[Tuple[int, str, int, Dict[str, Any]]]:
    """
    Build a sorted index of message timestamps for efficient lookup.
    NEW IMPLEMENTATION - Replaces snapchat_merger/audio_timestamp_matcher.py:207-245
    Original used seconds, we use milliseconds for better precision.
    
    Args:
        messages: The message history dictionary keyed by conversation ID
        
    Returns:
        Sorted list of (timestamp_ms, conv_id, msg_idx, message) tuples
    """
    timestamp_index = []
    
    for conv_id, message_list in messages.items():
        if not isinstance(message_list, list):
            continue
            
        for idx, message in enumerate(message_list):
            if not isinstance(message, dict):
                continue
                
            # Skip messages that already have media
            if message.get('matched_media_files'):
                continue
                
            # Get millisecond timestamp (field is misnamed as microseconds)
            timestamp_ms = message.get('Created(microseconds)')
            if not timestamp_ms:
                continue
                
            # Ensure it's an integer
            try:
                timestamp_ms = int(timestamp_ms)
            except (TypeError, ValueError):
                continue
                
            timestamp_index.append((timestamp_ms, conv_id, idx, message))
    
    # Sort by timestamp for binary search
    timestamp_index.sort(key=lambda x: x[0])
    logger.info(f"Built timestamp index with {len(timestamp_index)} messages")
    return timestamp_index


def find_closest_message_binary(
    mp4_timestamp_ms: int,
    timestamp_index: List[Tuple[int, str, int, Dict[str, Any]]],
    threshold_ms: int = 15000  # 15 seconds in milliseconds
) -> Optional[Tuple[str, int, Dict[str, Any], int]]:
    """
    Find the message closest to the MP4 timestamp using binary search.
    ADAPT FROM: snapchat_merger/audio_timestamp_matcher.py:247-314
    Modified to use milliseconds instead of seconds.
    
    Args:
        mp4_timestamp_ms: The timestamp from the MP4 file in milliseconds
        timestamp_index: Pre-built sorted timestamp index
        threshold_ms: Maximum time difference in milliseconds to consider a match
        
    Returns:
        A tuple of (conversation_id, message_index, message, time_diff_ms)
        or None if no match found within threshold
    """
    if not timestamp_index:
        return None
    
    # Binary search to find insertion point
    left, right = 0, len(timestamp_index) - 1
    
    while left <= right:
        mid = (left + right) // 2
        if timestamp_index[mid][0] < mp4_timestamp_ms:
            left = mid + 1
        else:
            right = mid - 1
    
    # Check candidates around the insertion point
    candidates = []
    
    # Check left side (earlier messages)
    idx = right
    while idx >= 0:
        ts_ms, conv_id, msg_idx, msg = timestamp_index[idx]
        diff_ms = mp4_timestamp_ms - ts_ms
        if diff_ms > threshold_ms:
            break
        candidates.append((conv_id, msg_idx, msg, diff_ms))
        idx -= 1
    
    # Check right side (later messages)
    idx = left
    while idx < len(timestamp_index):
        ts_ms, conv_id, msg_idx, msg = timestamp_index[idx]
        diff_ms = ts_ms - mp4_timestamp_ms
        if diff_ms > threshold_ms:
            break
        candidates.append((conv_id, msg_idx, msg, -diff_ms))  # Negative for later messages
        idx += 1
    
    # Find closest match
    if candidates:
        # Sort by absolute time difference
        return min(candidates, key=lambda x: abs(x[3]))
    
    return None


def match_mp4_timestamps(
    mp4_files: List[Path],
    messages: Dict[str, List[Dict[str, Any]]],
    threshold_seconds: int = 10,
    use_parallel: bool = False,
    max_workers: int = 4
) -> Dict[str, Tuple[str, int, int]]:
    """
    Match MP4 files to messages based on timestamps.
    
    Args:
        mp4_files: List of MP4 file paths to match
        messages: Message history dictionary
        threshold_seconds: Maximum time difference in seconds
        use_parallel: Whether to use parallel processing
        max_workers: Number of parallel workers
        
    Returns:
        Dictionary mapping MP4 filename to (conv_id, message_idx, time_diff_ms)
    """
    # Build timestamp index
    timestamp_index = build_millisecond_index(messages)
    
    if not timestamp_index:
        logger.warning("No messages with timestamps found for matching")
        return {}
    
    threshold_ms = threshold_seconds * 1000
    matches = {}
    
    if use_parallel and len(mp4_files) > 10:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        lock = threading.Lock()
        
        def process_mp4(mp4_file: Path) -> Optional[Tuple[str, Tuple[str, int, int]]]:
            timestamp_ms = extract_mp4_timestamp(mp4_file)
            if not timestamp_ms:
                return None
                
            match = find_closest_message_binary(timestamp_ms, timestamp_index, threshold_ms)
            if match:
                conv_id, msg_idx, msg, diff_ms = match
                return (mp4_file.name, (conv_id, msg_idx, diff_ms))
            return None
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_mp4, f) for f in mp4_files]
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    filename, match_data = result
                    with lock:
                        matches[filename] = match_data
    else:
        # Sequential processing
        for mp4_file in mp4_files:
            timestamp_ms = extract_mp4_timestamp(mp4_file)
            if not timestamp_ms:
                logger.debug(f"Could not extract timestamp from {mp4_file.name}")
                continue
                
            match = find_closest_message_binary(timestamp_ms, timestamp_index, threshold_ms)
            if match:
                conv_id, msg_idx, msg, diff_ms = match
                matches[mp4_file.name] = (conv_id, msg_idx, diff_ms)
                logger.debug(f"Matched {mp4_file.name} to message with {abs(diff_ms)/1000:.1f}s difference")
    
    logger.info(f"Matched {len(matches)} MP4 files to messages")
    return matches


def run_phase1(
    conversations_dir: Path,
    groups_dir: Path,
    media_dir: Path,
    output_dir: Path,
    timestamp_threshold: int = 10,
    max_workers: int = 4,
    use_parallel: bool = False
) -> Tuple[Phase1Stats, Dict[str, Any]]:
    """
    Run Phase 1: Media Mapping.
    
    This function orchestrates all Phase 1 operations:
    1. Extract media IDs from messages (T1.1)
    2. Build file mapping index (T1.2)
    3. Match MP4s using timestamp analysis (T1.3-T1.4)
    
    Args:
        conversations_dir: Path to output/conversations/ directory
        groups_dir: Path to output/groups/ directory
        media_dir: Directory containing media files
        output_dir: Output directory for results
        timestamp_threshold: Threshold for timestamp matching (seconds)
        max_workers: Number of parallel workers
        use_parallel: Whether to use parallel processing
        
    Returns:
        Tuple of (Phase1Stats, mapping_data)
    """
    stats = Phase1Stats()
    logger.info("=" * 60)
    logger.info("Starting Phase 1: Media Mapping")
    logger.info("=" * 60)
    
    # Load all conversations from individual files
    logger.info("Loading individual conversation files...")
    messages = load_all_conversations(conversations_dir, groups_dir)
    
    if not messages:
        logger.warning("No conversations found in output directories")
        return Phase1Stats(), {}
    
    logger.info(f"Loaded {len(messages)} conversations with {sum(len(msgs) for msgs in messages.values())} total messages")
    
    # ====================
    # T1.1: Extract Media IDs from messages
    # ====================
    logger.info("\n--- T1.1: Extracting Media IDs from messages ---")
    all_media_ids, extraction_stats = extract_media_ids_from_messages(messages)
    
    stats.total_media_ids = extraction_stats['total_ids']
    stats.unique_ids = len(all_media_ids)
    stats.pipe_separated_count = extraction_stats['pipe_separated']
    
    logger.info(f"Extracted {stats.unique_ids} unique Media IDs from {extraction_stats['messages_with_media']} messages")
    
    # ====================
    # T1.2: Build file mapping index
    # ====================
    logger.info("\n--- T1.2: Building file mapping index ---")
    media_index = create_media_index(media_dir, use_parallel=use_parallel, max_workers=max_workers)
    
    logger.info(f"Created index with {len(media_index)} Media IDs from files")
    
    # Count total media files
    all_media_files = list(media_dir.glob('*'))
    stats.total_media_files = len([f for f in all_media_files if f.is_file()])
    
    # Calculate mapping statistics
    matched_ids = all_media_ids.intersection(set(media_index.keys()))
    unmatched_ids = all_media_ids - set(media_index.keys())
    orphaned_files = set(media_index.keys()) - all_media_ids
    
    stats.ids_mapped = len(matched_ids)
    stats.ids_unmapped = len(unmatched_ids)
    stats.orphaned_files = len(orphaned_files)
    
    logger.info(f"Matched {stats.ids_mapped}/{stats.unique_ids} Media IDs ({stats.ids_mapped*100/stats.unique_ids:.1f}%)")
    logger.info(f"Unmatched IDs: {stats.ids_unmapped}")
    logger.info(f"Orphaned files: {len(orphaned_files)}")
    
    # ====================
    # T1.3-T1.4: MP4 Timestamp Matching
    # ====================
    logger.info("\n--- T1.3-T1.4: MP4 Timestamp Matching ---")
    
    # Find MP4 files that don't have Media IDs
    all_mp4s = list(media_dir.glob('*.mp4'))
    mp4s_without_ids = []
    
    for mp4_file in all_mp4s:
        # Check if this MP4 has a Media ID
        media_id = extract_media_id_from_filename(mp4_file.name)
        if not media_id or media_id not in matched_ids:
            mp4s_without_ids.append(mp4_file)
    
    logger.info(f"Found {len(mp4s_without_ids)} MP4 files without matched Media IDs")
    
    # Match MP4s using timestamps
    mp4_matches = {}
    if mp4s_without_ids:
        mp4_matches = match_mp4_timestamps(
            mp4s_without_ids,
            messages,
            threshold_seconds=timestamp_threshold,
            use_parallel=use_parallel,
            max_workers=max_workers
        )
        
        stats.mp4s_processed = len(mp4s_without_ids)
        stats.mp4s_matched = len(mp4_matches)
        
        logger.info(f"Matched {stats.mp4s_matched}/{stats.mp4s_processed} MP4 files using timestamps")
    
    # ====================
    # Compile final mapping data
    # ====================
    mapping_data = {
        'media_index': media_index,           # Media ID -> filename mapping
        'matched_ids': list(matched_ids),     # IDs found in both messages and files
        'unmatched_ids': list(unmatched_ids), # IDs in messages but not files
        'orphaned_files': list(orphaned_files), # Files without corresponding messages
        'mp4_matches': mp4_matches,           # MP4 filename -> (conv_id, msg_idx, diff_ms)
        'statistics': stats.to_dict()
    }
    
    # Save mapping data to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping_file = output_dir / 'phase1_mapping.json'
    
    # Create a serializable version of mapping_data
    serializable_data = {
        'media_index': mapping_data['media_index'],
        'matched_ids': mapping_data['matched_ids'],
        'unmatched_ids': mapping_data['unmatched_ids'],
        'orphaned_files': mapping_data['orphaned_files'],
        'mp4_matches': {k: {'conv_id': v[0], 'msg_idx': v[1], 'diff_ms': v[2]} 
                       for k, v in mapping_data['mp4_matches'].items()},
        'statistics': mapping_data['statistics']
    }
    
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, indent=2)
    
    logger.info(f"\nSaved mapping data to {mapping_file}")
    
    # ====================
    # Phase 1 Summary
    # ====================
    logger.info("\n" + "=" * 60)
    logger.info("Phase 1 Complete - Summary:")
    logger.info("=" * 60)
    logger.info(f"Total Media IDs extracted: {stats.total_media_ids}")
    logger.info(f"Unique Media IDs: {stats.unique_ids}")
    logger.info(f"IDs mapped to files: {stats.ids_mapped} ({stats.ids_mapped*100/stats.unique_ids:.1f}%)")
    logger.info(f"IDs not found in files: {stats.ids_unmapped}")
    logger.info(f"MP4s processed for timestamp matching: {stats.mp4s_processed}")
    logger.info(f"MP4s matched: {stats.mp4s_matched}")
    
    mapping_rate = (stats.ids_mapped / stats.unique_ids * 100) if stats.unique_ids > 0 else 0
    if mapping_rate >= 90:
        logger.info(f"✅ Mapping rate {mapping_rate:.1f}% - Excellent!")
    elif mapping_rate >= 70:
        logger.info(f"⚠️ Mapping rate {mapping_rate:.1f}% - Good but some files missing")
    else:
        logger.info(f"❌ Mapping rate {mapping_rate:.1f}% - Many files missing")
    
    return stats, mapping_data