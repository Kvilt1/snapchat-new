"""
Phase 1 T1.4: Timestamp Matching Module.
Matches MP4 files to messages based on timestamps.
"""

import logging
import threading
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from .mp4_processor import extract_mp4_timestamp

logger = logging.getLogger(__name__)


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