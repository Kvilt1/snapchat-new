#!/usr/bin/env python3
"""
Snapchat Data Merger V2 - Main Entry Point
Processes Snapchat data exports through 4 distinct phases
"""

import argparse
import sys
import logging
import time
import resource
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Snapchat Data Merger V2 - Process Snapchat data exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="By default, input data is read from ./input and output is written to ./output"
    )
    
    # Get the directory where main.py is located
    script_dir = Path(__file__).parent
    
    parser.add_argument(
        "--input",
        type=Path,
        default=script_dir / "input",
        help="Input directory containing Snapchat data (default: ./input)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "output",
        help="Output directory for processed data (default: ./output)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers for processing (default: 4)"
    )
    
    parser.add_argument(
        "--timestamp-threshold",
        type=int,
        default=10,
        help="Maximum time difference in seconds for MP4 matching (default: 10)"
    )
    
    parser.add_argument(
        "--no-overlay-merge",
        action="store_true",
        help="Skip overlay-media pair merging"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser


def validate_input_directory(data_dir: Path) -> Optional[Path]:
    """Validate that input directory contains exactly one data export folder.
    
    Returns the path to the export folder, or None if invalid.
    """
    if not data_dir.exists():
        logger.error(f"Input directory not found: {data_dir}")
        logger.info("Please create the input folder and place your Snapchat data export there")
        return None
    
    # Find folders that contain json/ and chat_media/ (ignore hidden files and README)
    export_folders = []
    for item in data_dir.iterdir():
        if item.is_dir() and item.name not in ['.gitkeep', 'README.md', '.DS_Store', '__pycache__', '.git']:
            json_dir = item / "json"
            media_dir = item / "chat_media"
            if json_dir.exists() and media_dir.exists():
                export_folders.append(item)
    
    if len(export_folders) == 0:
        logger.error("No Snapchat data export folder found in input directory")
        logger.info("Please place your entire Snapchat export folder inside ./input/")
        logger.info("Expected structure: input/[your-export-folder]/json/ and input/[your-export-folder]/chat_media/")
        logger.info("Example: input/mydat/json/ and input/mydat/chat_media/")
        return None
    elif len(export_folders) > 1:
        logger.error(f"Multiple data export folders found: {[f.name for f in export_folders]}")
        logger.info("Please keep only one Snapchat export folder in the input directory")
        return None
    else:
        actual_data_dir = export_folders[0]
        logger.info(f"Found Snapchat data export: {actual_data_dir.name}")
        
        # Validate the structure
        json_dir = actual_data_dir / "json"
        media_dir = actual_data_dir / "chat_media"
        
        # Check for required JSON files
        required_files = [
            json_dir / "chat_history.json",
            json_dir / "snap_history.json"
        ]
        
        for file_path in required_files:
            if not file_path.exists():
                logger.error(f"Required file not found: {file_path}")
                return None
        
        logger.info(f"Validation successful - using data from: {actual_data_dir}")
        return actual_data_dir


def main() -> int:
    """Main entry point for the Snapchat Merger V2."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Print header
    print("\n" + "=" * 50)
    print("Snapchat Data Merger V2")
    print("=" * 50 + "\n")
    
    # Use input argument for input directory
    input_dir = args.input
    
    # Validate and get actual data directory (the export folder inside input/)
    logger.info(f"Validating input directory: {input_dir}")
    data_dir = validate_input_directory(input_dir)
    if data_dir is None:
        return 1
    
    logger.info(f"Using data from: {data_dir}")
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {args.output}")
    
    # Track overall timing and memory
    overall_start_time = time.time()
    
    try:
        # Import phases here to avoid circular imports
        from phases.phase0_initial import run_phase0
        from phases.phase1_mapping import run_phase1
        from phases.phase2_organization import run_phase2
        from phases.phase3_validation import run_phase3
        from statistics.reporter_rich import StatisticsReporter
        
        # Initialize statistics reporter
        reporter = StatisticsReporter()
        
        # Phase 0: Initial Setup
        print("\n📋 Phase 0: Initial Setup")
        print("-" * 40)
        phase0_start = time.time()
        phase0_stats = run_phase0(
            data_dir=data_dir,
            output_dir=args.output,
            skip_overlay_merge=args.no_overlay_merge,
            max_workers=args.workers
        )
        phase0_duration = time.time() - phase0_start
        reporter.add_phase_stats(0, phase0_stats)
        reporter.add_phase_time(0, phase0_duration)
        print("✅ Phase 0 complete")
        
        # Phase 1: Media Mapping
        print("\n📍 Phase 1: Media Mapping")
        print("-" * 40)
        
        # Phase 1 loads from individual conversation files
        conversations_dir = args.output / 'conversations'
        groups_dir = args.output / 'groups'
        temp_media_dir = args.output / 'temp_media'
        
        phase1_start = time.time()
        phase1_stats, mapping_data = run_phase1(
            conversations_dir=conversations_dir,
            groups_dir=groups_dir,
            media_dir=temp_media_dir,
            output_dir=args.output,
            timestamp_threshold=args.timestamp_threshold,
            max_workers=args.workers,
            use_parallel=False  # Can be made configurable
        )
        phase1_duration = time.time() - phase1_start
        reporter.add_phase_stats(1, phase1_stats)
        reporter.add_phase_time(1, phase1_duration)
        print("✅ Phase 1 complete")
        
        # Phase 2: Media Organization
        print("\n🗂️ Phase 2: Media Organization")
        print("-" * 40)
        phase2_start = time.time()
        phase2_stats = run_phase2(
            output_dir=args.output,
            max_workers=args.workers
        )
        phase2_duration = time.time() - phase2_start
        reporter.add_phase_stats(2, phase2_stats)
        reporter.add_phase_time(2, phase2_duration)
        print("✅ Phase 2 complete")
        
        # Phase 3: Validation
        print("\n✅ Phase 3: Validation")
        print("-" * 40)
        phase3_start = time.time()
        phase3_stats = run_phase3(
            data_dir=data_dir,
            output_dir=args.output
        )
        phase3_duration = time.time() - phase3_start
        reporter.add_phase_stats(3, phase3_stats)
        reporter.add_phase_time(3, phase3_duration)
        print("✅ Phase 3 complete")
        
        # Track peak memory usage
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # On macOS, ru_maxrss is in bytes; on Linux, it's in kilobytes
        import platform
        if platform.system() == 'Darwin':
            peak_memory_mb = usage.ru_maxrss / 1024 / 1024  # Convert bytes to MB
        else:
            peak_memory_mb = usage.ru_maxrss / 1024  # Convert KB to MB
        reporter.set_peak_memory(peak_memory_mb)
        
        # Set overall processing time
        overall_duration = time.time() - overall_start_time
        reporter.set_processing_time(overall_duration)
        
        # Generate final report
        print("\n📊 Generating Statistics Report")
        print("-" * 40)
        reporter.print_enhanced_summary()  # Use enhanced summary instead
        reporter.save_report(args.output / "statistics.json")
        
        print("\n" + "=" * 50)
        print("✨ Processing complete!")
        print("=" * 50 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())