#!/usr/bin/env python3
"""
Test script for T1.4 - Timestamp Matching.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase1_mapping import (
    build_millisecond_index,
    find_closest_message_binary,
    match_mp4_timestamps,
    extract_mp4_timestamp
)

# Set up logging to see debug messages
logging.basicConfig(level=logging.INFO, format='%(message)s')


def load_test_messages() -> Dict[str, List[Dict[str, Any]]]:
    """Load sample messages from chat history."""
    chat_history_path = Path('/Users/rokur/Projects/snap-cursor/mydat/json/chat_history.json')
    
    if not chat_history_path.exists():
        print(f"Sample data not found at {chat_history_path}")
        return {}
    
    with open(chat_history_path, 'r', encoding='utf-8') as f:
        chat_data = json.load(f)
    
    # The structure is: {conversation_id: [messages]}
    # Each conversation is directly a list of messages
    messages = {}
    for conv_id, message_list in chat_data.items():
        if isinstance(message_list, list):
            messages[conv_id] = message_list
    
    return messages


def test_build_millisecond_index():
    """Test building the millisecond timestamp index."""
    print("Testing build_millisecond_index()...")
    print("=" * 60)
    
    # Load test messages
    messages = load_test_messages()
    
    if not messages:
        print("No messages loaded")
        return None
    
    print(f"Loaded {len(messages)} conversations")
    
    # Build index
    timestamp_index = build_millisecond_index(messages)
    
    print(f"Built index with {len(timestamp_index)} messages")
    
    if timestamp_index:
        # Show some examples
        print("\nFirst 5 messages in index:")
        for i, (ts_ms, conv_id, msg_idx, msg) in enumerate(timestamp_index[:5]):
            dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            msg_type = msg.get('Content Type', 'unknown')
            print(f"  {i+1}. {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC - {msg_type}")
        
        # Check timestamp ordering
        is_sorted = all(timestamp_index[i][0] <= timestamp_index[i+1][0] 
                       for i in range(len(timestamp_index)-1))
        
        if is_sorted:
            print("\n✅ Index is correctly sorted by timestamp")
        else:
            print("\n❌ Index is NOT sorted correctly!")
    
    print("\n✅ Millisecond index test completed!")
    return timestamp_index


def test_binary_search_matching(timestamp_index):
    """Test binary search for finding closest messages."""
    print("\nTesting find_closest_message_binary()...")
    print("=" * 60)
    
    if not timestamp_index:
        print("No timestamp index available")
        return
    
    # Get a timestamp from the middle of the index
    mid_idx = len(timestamp_index) // 2
    test_ts_ms = timestamp_index[mid_idx][0]
    
    dt = datetime.fromtimestamp(test_ts_ms / 1000, tz=timezone.utc)
    print(f"Test timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Test exact match
    match = find_closest_message_binary(test_ts_ms, timestamp_index, threshold_ms=10000)
    
    if match:
        conv_id, msg_idx, msg, diff_ms = match
        print(f"✅ Found exact match:")
        print(f"   Conversation: {conv_id[:30]}...")
        print(f"   Message index: {msg_idx}")
        print(f"   Time difference: {diff_ms/1000:.3f} seconds")
    
    # Test with offset (5 seconds later)
    offset_ts_ms = test_ts_ms + 5000
    match = find_closest_message_binary(offset_ts_ms, timestamp_index, threshold_ms=10000)
    
    if match:
        conv_id, msg_idx, msg, diff_ms = match
        print(f"\n✅ Found match with 5s offset:")
        print(f"   Time difference: {diff_ms/1000:.3f} seconds")
    
    # Test with large offset (should fail)
    large_offset_ts_ms = test_ts_ms + 20000  # 20 seconds
    match = find_closest_message_binary(large_offset_ts_ms, timestamp_index, threshold_ms=10000)
    
    if match:
        print(f"\n❌ Unexpectedly found match with 20s offset")
    else:
        print(f"\n✅ Correctly rejected match with 20s offset (outside threshold)")
    
    print("\n✅ Binary search test completed!")


def test_mp4_timestamp_matching():
    """Test matching MP4 files to messages."""
    print("\nTesting match_mp4_timestamps()...")
    print("=" * 60)
    
    # Load messages
    messages = load_test_messages()
    if not messages:
        print("No messages loaded")
        return
    
    # Find MP4 files
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        return
    
    mp4_files = list(media_dir.glob('*.mp4'))[:10]  # Test with first 10 MP4s
    
    if not mp4_files:
        print("No MP4 files found")
        return
    
    print(f"Testing with {len(mp4_files)} MP4 files")
    
    # Test matching
    matches = match_mp4_timestamps(
        mp4_files,
        messages,
        threshold_seconds=10,
        use_parallel=False
    )
    
    print(f"\nMatched {len(matches)} out of {len(mp4_files)} MP4 files")
    
    # Show some examples
    if matches:
        print("\nExample matches (first 3):")
        for i, (filename, (conv_id, msg_idx, diff_ms)) in enumerate(list(matches.items())[:3]):
            print(f"\n  {i+1}. {filename}")
            print(f"     Conversation: {conv_id[:30]}...")
            print(f"     Message index: {msg_idx}")
            print(f"     Time difference: {abs(diff_ms)/1000:.1f} seconds")
            
            # Verify the MP4 timestamp
            mp4_path = media_dir / filename
            mp4_ts_ms = extract_mp4_timestamp(mp4_path)
            if mp4_ts_ms:
                mp4_dt = datetime.fromtimestamp(mp4_ts_ms / 1000, tz=timezone.utc)
                print(f"     MP4 timestamp: {mp4_dt.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    # Calculate success rate
    success_rate = len(matches) / len(mp4_files) * 100 if mp4_files else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    if success_rate < 50:
        print("⚠️  Low match rate - this may be normal if MP4s don't correspond to messages")
    else:
        print("✅ Good match rate!")
    
    print("\n✅ MP4 timestamp matching test completed!")
    return matches


def test_performance():
    """Test performance of timestamp matching."""
    print("\nTesting performance...")
    print("=" * 60)
    
    import time
    
    messages = load_test_messages()
    if not messages:
        return
    
    # Time index building
    start = time.time()
    timestamp_index = build_millisecond_index(messages)
    build_time = time.time() - start
    
    print(f"Index building: {build_time*1000:.1f}ms for {len(timestamp_index)} messages")
    print(f"  Rate: {len(timestamp_index)/build_time:.0f} messages/second")
    
    # Time binary search (100 searches)
    if timestamp_index:
        test_timestamps = [timestamp_index[i][0] + 1000 for i in range(0, min(100, len(timestamp_index)), 10)]
        
        start = time.time()
        for ts in test_timestamps:
            find_closest_message_binary(ts, timestamp_index)
        search_time = time.time() - start
        
        avg_search_time = search_time / len(test_timestamps) * 1000
        print(f"\nBinary search: {avg_search_time:.3f}ms average per search")
        print(f"  Total: {search_time*1000:.1f}ms for {len(test_timestamps)} searches")
    
    print("\n✅ Performance test completed!")


def main():
    print("=" * 60)
    print("T1.4 Timestamp Matching Tests")
    print("=" * 60)
    print()
    
    # Run tests
    timestamp_index = test_build_millisecond_index()
    
    if timestamp_index:
        test_binary_search_matching(timestamp_index)
    
    matches = test_mp4_timestamp_matching()
    test_performance()
    
    print("\n" + "=" * 60)
    print("All T1.4 tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()