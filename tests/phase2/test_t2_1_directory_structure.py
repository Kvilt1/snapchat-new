#!/usr/bin/env python3
"""
Test script for T2.1 - Directory Structure
Tests the creation and verification of directory structure for Phase 2.
"""
import sys
import tempfile
import shutil
from pathlib import Path

# Add the snapchat-new directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phases.phase2_organization import (
    create_orphaned_directory,
    verify_conversation_directories,
    verify_directory_permissions,
    setup_directory_structure,
    Phase2Stats
)


def test_create_orphaned_directory():
    """Test creating the orphaned directory."""
    print("Testing orphaned directory creation...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        
        # Test creating orphaned directory
        result = create_orphaned_directory(output_dir)
        assert result == True, "Failed to create orphaned directory"
        
        # Verify it exists
        orphaned_dir = output_dir / "orphaned"
        assert orphaned_dir.exists(), "Orphaned directory does not exist"
        assert orphaned_dir.is_dir(), "Orphaned path is not a directory"
        
        # Test idempotency - should work when called again
        result = create_orphaned_directory(output_dir)
        assert result == True, "Failed on second call (should be idempotent)"
        
    print("✅ Orphaned directory creation test passed")


def test_verify_conversation_directories():
    """Test verification of conversation and group directories."""
    print("Testing conversation directory verification...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        
        # Test with no directories
        conv_count, group_count = verify_conversation_directories(output_dir)
        assert conv_count == 0, "Should find 0 conversations when dir doesn't exist"
        assert group_count == 0, "Should find 0 groups when dir doesn't exist"
        
        # Create some test conversation directories
        conversations_dir = output_dir / "conversations"
        conversations_dir.mkdir()
        for i in range(3):
            (conversations_dir / f"2025-01-{20+i:02d} - user{i}").mkdir()
        
        # Create some test group directories
        groups_dir = output_dir / "groups"
        groups_dir.mkdir()
        for i in range(2):
            (groups_dir / f"2025-01-20 - group{i}").mkdir()
        
        # Test counting
        conv_count, group_count = verify_conversation_directories(output_dir)
        assert conv_count == 3, f"Expected 3 conversations, found {conv_count}"
        assert group_count == 2, f"Expected 2 groups, found {group_count}"
        
    print("✅ Conversation directory verification test passed")


def test_verify_directory_permissions():
    """Test directory permission verification."""
    print("Testing directory permission verification...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test"
        test_dir.mkdir()
        
        # Test valid directory with permissions
        result = verify_directory_permissions(test_dir)
        assert result == True, "Failed to verify permissions for valid directory"
        
        # Test non-existent directory
        non_existent = Path(temp_dir) / "does_not_exist"
        result = verify_directory_permissions(non_existent)
        assert result == False, "Should fail for non-existent directory"
        
        # Test file instead of directory
        test_file = Path(temp_dir) / "file.txt"
        test_file.touch()
        result = verify_directory_permissions(test_file)
        assert result == False, "Should fail for file instead of directory"
        
    print("✅ Directory permission verification test passed")


def test_setup_directory_structure():
    """Test complete directory structure setup."""
    print("Testing complete directory structure setup...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        stats = Phase2Stats()
        
        # Create Phase 0 structure first
        conversations_dir = output_dir / "conversations"
        conversations_dir.mkdir()
        (conversations_dir / "2025-01-20 - testuser").mkdir()
        
        groups_dir = output_dir / "groups"
        groups_dir.mkdir()
        (groups_dir / "2025-01-20 - testgroup").mkdir()
        
        temp_media_dir = output_dir / "temp_media"
        temp_media_dir.mkdir()
        
        # Test setup
        result = setup_directory_structure(output_dir, stats)
        assert result == True, "Directory structure setup failed"
        
        # Verify stats
        assert stats.directories_created == 2, f"Expected 2 directories, got {stats.directories_created}"
        assert stats.orphaned_dir_created == True, "Orphaned directory not created"
        assert len(stats.errors) == 0, f"Unexpected errors: {stats.errors}"
        
        # Verify orphaned directory exists
        orphaned_dir = output_dir / "orphaned"
        assert orphaned_dir.exists(), "Orphaned directory not created"
        
    print("✅ Complete directory structure setup test passed")


def test_with_real_structure():
    """Test with structure similar to real output."""
    print("Testing with realistic directory structure...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)
        
        # Create realistic Phase 0 output structure
        conversations_dir = output_dir / "conversations"
        conversations_dir.mkdir()
        
        # Create multiple conversation folders
        conv_names = [
            "2024-07-21 - alice",
            "2024-08-15 - bob",
            "2024-09-10 - charlie",
            "2024-10-05 - david",
            "2024-11-20 - emma"
        ]
        
        for name in conv_names:
            conv_folder = conversations_dir / name
            conv_folder.mkdir()
            # Add a conversation.json file
            (conv_folder / "conversation.json").write_text('{"messages": []}')
        
        # Create group folders
        groups_dir = output_dir / "groups"
        groups_dir.mkdir()
        
        group_names = [
            "2024-07-25 - Study Group",
            "2024-08-30 - Project Team"
        ]
        
        for name in group_names:
            group_folder = groups_dir / name
            group_folder.mkdir()
            (group_folder / "conversation.json").write_text('{"messages": []}')
        
        # Create temp_media directory
        temp_media_dir = output_dir / "temp_media"
        temp_media_dir.mkdir()
        
        # Test directory structure setup
        stats = Phase2Stats()
        result = setup_directory_structure(output_dir, stats)
        
        assert result == True, "Setup failed with realistic structure"
        assert stats.directories_created == 7, f"Expected 7 directories (5 conv + 2 groups), got {stats.directories_created}"
        assert stats.orphaned_dir_created == True, "Orphaned directory not created"
        assert (output_dir / "orphaned").exists(), "Orphaned directory missing"
        
        # Verify permissions for all directories
        for conv_name in conv_names:
            assert verify_directory_permissions(conversations_dir / conv_name), f"Permission issue with {conv_name}"
        
        for group_name in group_names:
            assert verify_directory_permissions(groups_dir / group_name), f"Permission issue with {group_name}"
        
    print("✅ Realistic structure test passed")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("Testing T2.1: Directory Structure")
    print("="*50 + "\n")
    
    test_create_orphaned_directory()
    test_verify_conversation_directories()
    test_verify_directory_permissions()
    test_setup_directory_structure()
    test_with_real_structure()
    
    print("\n" + "="*50)
    print("✅ All T2.1 tests passed!")
    print("="*50)