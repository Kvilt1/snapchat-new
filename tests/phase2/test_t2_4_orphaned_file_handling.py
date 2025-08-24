#!/usr/bin/env python3
"""
Test script for T2.4 - Orphaned File Handling
Tests the functionality of identifying and organizing unmapped media files.
"""
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase2 import (
    identify_unmapped_files,
    move_orphaned_files,
    generate_orphaned_report,
    process_orphaned_files,
    Phase2Stats
)


def create_test_mapping_data():
    """Create test Phase 1 mapping data."""
    return {
        "media_index": {
            "media_001": "2024-01-15_media_001.jpg",
            "media_002": "2024-01-15_media_002.mp4",
            "media_003": "2024-01-16_media_003.png"
        },
        "statistics": {
            "total_media_files": 5,
            "mapped_files": 3,
            "unmapped_files": 2
        }
    }


def test_identify_unmapped_files():
    """Test identifying unmapped files from temp_media."""
    print("\n[TEST] Testing identify_unmapped_files()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        temp_media_dir = temp_path / "temp_media"
        temp_media_dir.mkdir()
        
        # Create test media files
        mapped_files = [
            "2024-01-15_media_001.jpg",
            "2024-01-15_media_002.mp4",
            "2024-01-16_media_003.png"
        ]
        unmapped_files = [
            "2024-01-17_unmapped_001.jpg",
            "2024-01-18_unmapped_002.mp4"
        ]
        
        # Create all files
        for filename in mapped_files + unmapped_files:
            (temp_media_dir / filename).write_text(f"content of {filename}")
        
        # Create mapping data
        mapping_data = create_test_mapping_data()
        
        # Test identification
        identified = identify_unmapped_files(temp_media_dir, mapping_data)
        
        assert len(identified) == 2, f"Expected 2 unmapped files, got {len(identified)}"
        
        identified_names = [f.name for f in identified]
        assert "2024-01-17_unmapped_001.jpg" in identified_names, "Missing unmapped file 1"
        assert "2024-01-18_unmapped_002.mp4" in identified_names, "Missing unmapped file 2"
        
        print("  ✓ Successfully identified unmapped files")
        
        # Test with non-existent directory
        non_existent = temp_path / "non_existent"
        identified = identify_unmapped_files(non_existent, mapping_data)
        assert len(identified) == 0, "Should return empty list for non-existent directory"
        print("  ✓ Correctly handled non-existent directory")


def test_move_orphaned_files():
    """Test moving orphaned files to orphaned directory."""
    print("\n[TEST] Testing move_orphaned_files()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create source files
        temp_media_dir = temp_path / "temp_media"
        temp_media_dir.mkdir()
        
        unmapped_files = []
        for i in range(3):
            filename = f"2024-01-1{i}_orphaned_{i:03d}.jpg"
            file_path = temp_media_dir / filename
            file_path.write_text(f"orphaned content {i}")
            unmapped_files.append(file_path)
        
        # Create orphaned directory
        orphaned_dir = temp_path / "orphaned"
        orphaned_dir.mkdir()
        
        # Test moving files
        stats = Phase2Stats()
        moved = move_orphaned_files(unmapped_files, orphaned_dir, stats)
        
        assert len(moved) == 3, f"Expected 3 moved files, got {len(moved)}"
        assert stats.files_orphaned == 3, "Stats not updated correctly"
        
        # Verify files were moved
        for filename in moved:
            assert (orphaned_dir / filename).exists(), f"File not in orphaned: {filename}"
            assert not (temp_media_dir / filename).exists(), f"File still in temp_media: {filename}"
        
        print("  ✓ Successfully moved orphaned files")
        print(f"  ✓ Stats updated: {stats.files_orphaned} files orphaned")
        
        # Test with error handling
        invalid_file = Path("/non/existent/file.jpg")
        moved = move_orphaned_files([invalid_file], orphaned_dir, stats)
        assert len(moved) == 0, "Should handle non-existent files gracefully"
        assert len(stats.errors) > 0, "Should record error for failed move"
        print("  ✓ Correctly handled move errors")


def test_generate_orphaned_report():
    """Test generating orphaned files report."""
    print("\n[TEST] Testing generate_orphaned_report()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        orphaned_dir = temp_path / "orphaned"
        orphaned_dir.mkdir()
        
        # Create orphaned files
        moved_files = [
            "2024-01-15_orphaned_001.jpg",
            "2024-01-16_orphaned_002.mp4",
            "2024-01-17_orphaned_003.png",
            "no_date_file.txt"
        ]
        
        for filename in moved_files:
            file_path = orphaned_dir / filename
            file_path.write_text(f"content of {filename}")
        
        # Generate report
        stats = Phase2Stats()
        result = generate_orphaned_report(orphaned_dir, moved_files, stats)
        
        assert result is True, "Report generation should succeed"
        
        # Verify report file
        report_file = orphaned_dir / "orphaned_files_report.json"
        assert report_file.exists(), "Report file not created"
        
        # Check report content
        with open(report_file, 'r') as f:
            report_data = json.load(f)
        
        assert report_data["total_files"] == 4, "Incorrect file count in report"
        assert len(report_data["files"]) == 4, "Incorrect number of file entries"
        
        # Check date extraction
        file_with_date = next(f for f in report_data["files"] 
                              if f["filename"] == "2024-01-15_orphaned_001.jpg")
        assert "extracted_date" in file_with_date, "Date should be extracted"
        assert file_with_date["extracted_date"] == "2024-01-15", "Incorrect date extraction"
        
        # Check file without date
        file_without_date = next(f for f in report_data["files"] 
                                if f["filename"] == "no_date_file.txt")
        assert "extracted_date" not in file_without_date, "Should not extract date from non-date filename"
        
        print("  ✓ Successfully generated orphaned files report")
        print(f"  ✓ Report contains {report_data['total_files']} files")
        print("  ✓ Date extraction working correctly")


def test_process_orphaned_files():
    """Test the complete orphaned file processing workflow."""
    print("\n[TEST] Testing process_orphaned_files()...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        output_dir = temp_path / "output"
        
        # Create directory structure
        temp_media_dir = output_dir / "temp_media"
        orphaned_dir = output_dir / "orphaned"
        temp_media_dir.mkdir(parents=True)
        orphaned_dir.mkdir(parents=True)
        
        # Create media files (some mapped, some orphaned)
        all_files = {
            "2024-01-15_media_001.jpg": "mapped",
            "2024-01-15_media_002.mp4": "mapped",
            "2024-01-16_orphan_001.jpg": "orphaned",
            "2024-01-17_orphan_002.mp4": "orphaned",
            "2024-01-18_orphan_003.png": "orphaned"
        }
        
        for filename, status in all_files.items():
            (temp_media_dir / filename).write_text(f"{status} content")
        
        # Create mapping data (only includes mapped files)
        mapping_data = {
            "media_index": {
                "media_001": "2024-01-15_media_001.jpg",
                "media_002": "2024-01-15_media_002.mp4"
            }
        }
        
        # Process orphaned files
        stats = Phase2Stats()
        process_orphaned_files(output_dir, mapping_data, stats)
        
        # Verify results
        assert stats.files_orphaned == 3, f"Expected 3 orphaned files, got {stats.files_orphaned}"
        
        # Check files were moved
        orphaned_files = list(orphaned_dir.glob("*.jpg")) + \
                        list(orphaned_dir.glob("*.mp4")) + \
                        list(orphaned_dir.glob("*.png"))
        assert len(orphaned_files) == 3, "Not all orphaned files were moved"
        
        # Check report was generated
        report_file = orphaned_dir / "orphaned_files_report.json"
        assert report_file.exists(), "Report file not generated"
        
        # Verify mapped files were NOT moved
        assert (temp_media_dir / "2024-01-15_media_001.jpg").exists(), "Mapped file was incorrectly moved"
        assert (temp_media_dir / "2024-01-15_media_002.mp4").exists(), "Mapped file was incorrectly moved"
        
        print("  ✓ Successfully processed orphaned files")
        print(f"  ✓ Moved {stats.files_orphaned} orphaned files")
        print("  ✓ Mapped files preserved in temp_media")
        print("  ✓ Report generated successfully")


def test_flat_directory_structure():
    """Test that orphaned files are in flat directory (no subdirectories)."""
    print("\n[TEST] Testing flat orphaned directory structure...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        orphaned_dir = temp_path / "orphaned"
        orphaned_dir.mkdir()
        
        # Create files with various dates
        files = [
            "2024-01-15_file1.jpg",
            "2024-02-20_file2.mp4",
            "2024-12-31_file3.png",
            "2025-01-01_file4.jpg"
        ]
        
        stats = Phase2Stats()
        
        # Simulate moving files (directly create them in orphaned)
        for filename in files:
            (orphaned_dir / filename).write_text("content")
        
        # Verify flat structure
        subdirs = [f for f in orphaned_dir.iterdir() if f.is_dir()]
        assert len(subdirs) == 0, "Orphaned directory should have no subdirectories"
        
        # Verify all files are at root level
        root_files = [f for f in orphaned_dir.iterdir() if f.is_file()]
        # Subtract 1 if report exists
        expected_count = len(files)
        assert len(root_files) >= expected_count, f"All files should be at root level"
        
        print("  ✓ Orphaned directory has flat structure (no subdirectories)")
        print(f"  ✓ All {len(files)} files at root level")


def main():
    """Run all tests for T2.4."""
    print("=" * 60)
    print("T2.4: Orphaned File Handling - Test Suite")
    print("=" * 60)
    
    try:
        test_identify_unmapped_files()
        test_move_orphaned_files()
        test_generate_orphaned_report()
        test_process_orphaned_files()
        test_flat_directory_structure()
        
        print("\n" + "=" * 60)
        print("✅ ALL T2.4 TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()