#!/usr/bin/env python3
"""
Test script for T1.1.3 - Media ID extraction from filenames.
"""

import sys
from pathlib import Path

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase1 import extract_media_id_from_filename


def test_extract_media_id_from_filename():
    """Test the media ID extraction from different filename patterns."""
    print("Testing extract_media_id_from_filename()...")
    
    # Test case 1: b~ pattern
    filename = "2025-07-27_b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ.jpeg"
    result = extract_media_id_from_filename(filename)
    expected = "b~EiASFU8zdmJFSGUxRDR6MzV1VUJBelNRQTIBCEgCUARgAQ"
    assert result == expected, f"b~ pattern failed: got {result}, expected {expected}"
    print(f"✅ b~ pattern: {result[:30]}...")
    
    # Test case 2: media~ pattern
    filename = "2025-07-27_media~28E0FFB8-5182-4D9D-92E1-DD941C881FC5.mp4"
    result = extract_media_id_from_filename(filename)
    expected = "media~28E0FFB8-5182-4D9D-92E1-DD941C881FC5"
    assert result == expected, f"media~ pattern failed: got {result}, expected {expected}"
    print(f"✅ media~ pattern: {result}")
    
    # Test case 3: overlay~ pattern
    filename = "2025-07-27_overlay~7E80A0BA-875C-49B0-8F4A-865EB6F8EC21.webp"
    result = extract_media_id_from_filename(filename)
    expected = "overlay~7E80A0BA-875C-49B0-8F4A-865EB6F8EC21"
    assert result == expected, f"overlay~ pattern failed: got {result}, expected {expected}"
    print(f"✅ overlay~ pattern: {result}")
    
    # Test case 4: media~zip- pattern
    filename = "2025-07-30_media~zip-C63E6B4D-4DF6-4C2C-A331-A49E4F1C0109.mp4"
    result = extract_media_id_from_filename(filename)
    expected = "media~zip-C63E6B4D-4DF6-4C2C-A331-A49E4F1C0109"
    assert result == expected, f"media~zip- pattern failed: got {result}, expected {expected}"
    print(f"✅ media~zip- pattern: {result}")
    
    # Test case 5: thumbnail (should be excluded)
    filename = "2025-07-27_thumbnail~something.jpeg"
    result = extract_media_id_from_filename(filename)
    assert result is None, f"thumbnail pattern should return None, got {result}"
    print(f"✅ thumbnail excluded: {result}")
    
    # Test case 6: No pattern
    filename = "regular_file.txt"
    result = extract_media_id_from_filename(filename)
    assert result is None, f"No pattern should return None, got {result}"
    print(f"✅ No pattern: {result}")
    
    print("\nAll extract_media_id_from_filename tests passed!")


def test_with_real_files():
    """Test with actual media files from test_output."""
    print("\nTesting with real media files...")
    
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        print("Run Phase 0 first to create test data")
        return
    
    # Collect some sample files
    media_files = list(media_dir.glob('*.mp4'))[:5] + \
                  list(media_dir.glob('*.jpeg'))[:5] + \
                  list(media_dir.glob('*.png'))[:5] + \
                  list(media_dir.glob('*.webp'))[:5]
    
    if not media_files:
        print("No media files found in test_output")
        return
    
    # Extract IDs from real files
    id_counts = {
        'b~': 0,
        'media~': 0,
        'overlay~': 0,
        'media~zip-': 0,
        'none': 0
    }
    
    print(f"Processing {len(media_files)} media files...")
    for file in media_files:
        media_id = extract_media_id_from_filename(file.name)
        if media_id:
            if media_id.startswith('b~'):
                id_counts['b~'] += 1
            elif media_id.startswith('media~zip-'):
                id_counts['media~zip-'] += 1
            elif media_id.startswith('media~'):
                id_counts['media~'] += 1
            elif media_id.startswith('overlay~'):
                id_counts['overlay~'] += 1
        else:
            id_counts['none'] += 1
    
    print("\nID extraction results:")
    print(f"  b~ IDs: {id_counts['b~']}")
    print(f"  media~ IDs: {id_counts['media~']}")
    print(f"  overlay~ IDs: {id_counts['overlay~']}")
    print(f"  media~zip- IDs: {id_counts['media~zip-']}")
    print(f"  No ID found: {id_counts['none']}")
    
    # Show some examples
    print("\nExample extracted IDs:")
    examples_shown = 0
    for file in media_files[:10]:
        media_id = extract_media_id_from_filename(file.name)
        if media_id and examples_shown < 5:
            print(f"  {file.name[:40]}... -> {media_id[:40]}...")
            examples_shown += 1
    
    print("\n✅ Real file test completed!")


def main():
    print("=" * 60)
    print("T1.1.3 Media ID Extraction from Filenames Tests")
    print("=" * 60)
    print()
    
    # Run tests
    test_extract_media_id_from_filename()
    test_with_real_files()
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()