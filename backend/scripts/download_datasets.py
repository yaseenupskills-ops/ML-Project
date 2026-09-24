#!/usr/bin/env python3
"""
Dataset download script for UR Fall Detection and Le2i Fall datasets.
Since direct automated downloads may require authentication or have changing URLs,
this script provides instructions and creates the directory structure.
"""

import os
import sys
from pathlib import Path

def setup_directories():
    """Create the required directory structure."""
    base_dir = Path(__file__).parent.parent
    urfd_dir = base_dir / "data" / "raw" / "URFD"
    le2i_dir = base_dir / "data" / "raw" / "Le2i"
    
    urfd_dir.mkdir(parents=True, exist_ok=True)
    le2i_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Created directories:")
    print(f"  {urfd_dir}")
    print(f"  {le2i_dir}")
    
    return urfd_dir, le2i_dir

def print_download_instructions():
    """Print manual download instructions for both datasets."""
    print("\n" + "="*80)
    print("DATASET DOWNLOAD INSTRUCTIONS")
    print("="*80)
    
    print("\n1. UR Fall Detection Dataset:")
    print("   Primary site: http://fenix.univ.rzeszow.pl/~mkepski/ds/uf.html")
    print("   Alternative mirrors (search for):")
    print("   - 'UR Fall Detection Dataset' on IEEE DataPort")
    print("   - 'UR Fall Detection Dataset' on Kaggle")
    print("   Contains: RGB-D videos of falls and ADLs (activities of daily living)")
    print("   Format: AVI videos + annotation files")
    
    print("\n2. Le2i Fall Detection Dataset:")
    print("   Primary site: https://le2i.cnrs.fr/Fall-detection-Dataset/")
    print("   Alternative: Search 'Le2i Fall Detection Dataset'")
    print("   Contains: Multi-view camera recordings of falls and ADLs")
    print("   Format: Video sequences (various formats) + skeleton data")
    
    print("\n" + "-"*80)
    print("MANUAL STEPS:")
    print("-"*80)
    print("1. Download both datasets manually from the above sources")
    print("2. Extract contents to:")
    print("   - data/raw/URFD/")
    print("   - data/raw/Le2i/")
    print("3. Ensure each dataset folder contains its respective videos/annotations")
    print("4. Return here and re-run any preprocessing scripts")
    print("\nNOTE: These datasets contain actor-performed falls in controlled environments.")
    print("      Real-world performance may vary - this is a known limitation.")
    print("="*80)

def verify_directories(urfd_dir, le2i_dir):
    """Check if directories have content and report status."""
    print("\n" + "-"*80)
    print("DIRECTORY STATUS")
    print("-"*80)
    
    urfd_count = len(list(urfd_dir.rglob("*"))) if urfd_dir.exists() else 0
    le2i_count = len(list(le2i_dir.rglob("*"))) if le2i_dir.exists() else 0
    
    print(f"URFD files: {urfd_count} items in {urfd_dir}")
    print(f"Le2i files: {le2i_count} items in {le2i_dir}")
    
    if urfd_count == 0:
        print("⚠️  URFD directory is empty - please download dataset")
    else:
        print("✅ URFD directory has content")
        
    if le2i_count == 0:
        print("⚠️  Le2i directory is empty - please download dataset")
    else:
        print("✅ Le2i directory has content")
    
    return urfd_count > 0 and le2i_count > 0

def main():
    """Main execution function."""
    print("Fall Detection Dataset Setup")
    print("="*50)
    
    # Setup directories
    urfd_dir, le2i_dir = setup_directories()
    
    # Show download instructions
    print_download_instructions()
    
    # Check current status
    both_ready = verify_directories(urfd_dir, le2i_dir)
    
    if both_ready:
        print("\n🎉 Both datasets appear to be present!")
        print("You can now proceed with feature extraction.")
    else:
        print("\n📥 Please download the datasets as instructed above.")
        print("After downloading, re-run this script to verify.")
    
    return 0 if both_ready else 1

if __name__ == "__main__":
    sys.exit(main())