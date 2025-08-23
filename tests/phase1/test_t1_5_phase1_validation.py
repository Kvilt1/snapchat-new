#!/usr/bin/env python3
"""
Test script for T1.5 - Phase 1 Validation and Integration.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase1_mapping import run_phase1

# Set up logging to see info messages
logging.basicConfig(level=logging.INFO, format='%(message)s')


def test_phase1_integration():
    """Test the complete Phase 1 pipeline."""
    print("=" * 60)
    print("Testing Phase 1 Integration")
    print("=" * 60)
    print()
    
    # Set up paths
    chat_history_path = Path('/Users/rokur/Projects/snap-cursor/mydat/json/chat_history.json')
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    output_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/phase1_results')
    
    # Check if required files exist
    if not chat_history_path.exists():
        print(f"❌ Chat history not found: {chat_history_path}")
        return False
    
    if not media_dir.exists():
        print(f"❌ Media directory not found: {media_dir}")
        print("Run Phase 0 first to create test data")
        return False
    
    print(f"Chat history: {chat_history_path}")
    print(f"Media directory: {media_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Run Phase 1
    try:
        stats, mapping_data = run_phase1(
            chat_history_path=chat_history_path,
            media_dir=media_dir,
            output_dir=output_dir,
            timestamp_threshold=10,
            max_workers=4,
            use_parallel=False
        )
        
        print("\n" + "=" * 60)
        print("Phase 1 Validation Results")
        print("=" * 60)
        
        # Validate statistics
        print("\n📊 Statistics Validation:")
        
        # Check if we extracted Media IDs
        if stats.unique_ids > 0:
            print(f"✅ Extracted {stats.unique_ids} unique Media IDs")
        else:
            print(f"❌ No Media IDs extracted")
            return False
        
        # Check mapping rate
        mapping_rate = (stats.ids_mapped / stats.unique_ids * 100) if stats.unique_ids > 0 else 0
        if mapping_rate >= 90:
            print(f"✅ Excellent mapping rate: {mapping_rate:.1f}%")
        elif mapping_rate >= 70:
            print(f"⚠️ Good mapping rate: {mapping_rate:.1f}%")
        else:
            print(f"❌ Low mapping rate: {mapping_rate:.1f}%")
        
        # Check MP4 timestamp matching
        if stats.mp4s_processed > 0:
            mp4_match_rate = (stats.mp4s_matched / stats.mp4s_processed * 100)
            print(f"✅ MP4 matching: {stats.mp4s_matched}/{stats.mp4s_processed} ({mp4_match_rate:.1f}%)")
        else:
            print("ℹ️ No MP4s needed timestamp matching")
        
        # Validate output file
        mapping_file = output_dir / 'phase1_mapping.json'
        if mapping_file.exists():
            print(f"\n✅ Mapping data saved to: {mapping_file}")
            
            # Load and validate the saved data
            with open(mapping_file, 'r') as f:
                saved_data = json.load(f)
            
            print(f"   - Media index entries: {len(saved_data['media_index'])}")
            print(f"   - Matched IDs: {len(saved_data['matched_ids'])}")
            print(f"   - Unmatched IDs: {len(saved_data['unmatched_ids'])}")
            print(f"   - Orphaned files: {len(saved_data['orphaned_files'])}")
            print(f"   - MP4 matches: {len(saved_data['mp4_matches'])}")
        else:
            print(f"❌ Mapping file not created")
            return False
        
        # Validate data integrity
        print("\n🔍 Data Integrity Checks:")
        
        # Check that matched + unmatched = total unique
        total_check = stats.ids_mapped + stats.ids_unmapped
        if total_check == stats.unique_ids:
            print(f"✅ ID accounting correct: {stats.ids_mapped} + {stats.ids_unmapped} = {stats.unique_ids}")
        else:
            print(f"❌ ID accounting mismatch: {stats.ids_mapped} + {stats.ids_unmapped} ≠ {stats.unique_ids}")
        
        # Check that statistics match the actual data
        if len(mapping_data['matched_ids']) == stats.ids_mapped:
            print(f"✅ Matched IDs count consistent")
        else:
            print(f"❌ Matched IDs count mismatch")
        
        if len(mapping_data['unmatched_ids']) == stats.ids_unmapped:
            print(f"✅ Unmatched IDs count consistent")
        else:
            print(f"❌ Unmatched IDs count mismatch")
        
        # Final validation result
        print("\n" + "=" * 60)
        print("Phase 1 Validation Summary")
        print("=" * 60)
        
        validation_passed = (
            stats.unique_ids > 0 and
            mapping_rate >= 70 and
            mapping_file.exists() and
            total_check == stats.unique_ids
        )
        
        if validation_passed:
            print("✅ Phase 1 validation PASSED - Ready for Phase 2!")
            print(f"   - {stats.unique_ids} Media IDs extracted")
            print(f"   - {mapping_rate:.1f}% mapping rate")
            print(f"   - {stats.mp4s_matched} MP4s matched via timestamps")
            print(f"   - Mapping data saved successfully")
        else:
            print("❌ Phase 1 validation FAILED")
        
        return validation_passed
        
    except Exception as e:
        print(f"❌ Error running Phase 1: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase1_functions():
    """Test individual Phase 1 functions."""
    print("\n" + "=" * 60)
    print("Testing Individual Phase 1 Functions")
    print("=" * 60)
    
    from phases.phase1_mapping import (
        split_pipe_separated_ids,
        extract_media_id_from_filename,
        create_media_index,
        parse_mp4_timestamp_binary,
        build_millisecond_index
    )
    
    # Test T1.1 functions
    print("\n📝 T1.1 - Media ID Extraction:")
    test_ids = "id1 | id2 | id3"
    result = split_pipe_separated_ids(test_ids)
    if result == ["id1", "id2", "id3"]:
        print("✅ Pipe-separated ID parsing works")
    else:
        print(f"❌ Pipe-separated ID parsing failed: {result}")
    
    # Test T1.1.3 function
    test_filename = "2025-07-19_b~EiASFUMwdUoxN2dENEZOUzJ4ODhCSmZzRjIBCEgCUARgAQ.mp4"
    media_id = extract_media_id_from_filename(test_filename)
    if media_id and media_id.startswith("b~"):
        print(f"✅ Media ID extraction works: {media_id[:30]}...")
    else:
        print(f"❌ Media ID extraction failed")
    
    # Test T1.2 function
    print("\n📝 T1.2 - File Mapping:")
    media_dir = Path('/Users/rokur/Projects/snap-cursor/test_output/temp_media')
    if media_dir.exists():
        index = create_media_index(media_dir)
        if len(index) > 0:
            print(f"✅ Media index creation works: {len(index)} entries")
        else:
            print("❌ Media index creation failed")
    
    # Test T1.3 function
    print("\n📝 T1.3 - MP4 Timestamp Extraction:")
    mp4_files = list(media_dir.glob('*.mp4'))[:1] if media_dir.exists() else []
    if mp4_files:
        timestamp = parse_mp4_timestamp_binary(mp4_files[0])
        if timestamp:
            print(f"✅ MP4 timestamp extraction works: {timestamp}")
        else:
            print("❌ MP4 timestamp extraction failed")
    
    print("\n✅ Individual function tests completed")


def main():
    print("=" * 60)
    print("T1.5 Phase 1 Validation Tests")
    print("=" * 60)
    print()
    
    # Test individual functions
    test_phase1_functions()
    
    # Test complete integration
    success = test_phase1_integration()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All Phase 1 validation tests PASSED!")
    else:
        print("⚠️ Some Phase 1 validation tests failed")
    print("=" * 60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())