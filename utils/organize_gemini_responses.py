#!/usr/bin/env python3
"""
Script to organize Gemini responses into versioned directories
"""
import os
import shutil
from datetime import datetime
from pathlib import Path

def organize_gemini_responses():
    """Organize Gemini responses into versioned directories"""
    
    base_dir = Path("logs/gemini_responses")
    
    if not base_dir.exists():
        print("Gemini responses directory doesn't exist")
        return
    
    # Get all response files
    response_files = list(base_dir.glob("gemini_response_*.txt"))
    
    if not response_files:
        print("No response files found")
        return
    
    # Group files by date
    files_by_date = {}
    for file in response_files:
        # Extract timestamp from filename: gemini_response_20250902_113401_batch_67.txt
        parts = file.stem.split('_')
        if len(parts) >= 3:
            date_str = parts[2]  # 20250902
            if date_str not in files_by_date:
                files_by_date[date_str] = []
            files_by_date[date_str].append(file)
    
    # Create directories and move files
    for date_str, files in files_by_date.items():
        if len(files) < 5:  # Skip if very few files (might be test runs)
            continue
            
        # Create versioned directory
        version_dir = base_dir / f"run_{date_str}"
        version_dir.mkdir(exist_ok=True)
        
        # Move files
        moved_count = 0
        for file in files:
            try:
                dest = version_dir / file.name
                if not dest.exists():
                    shutil.move(str(file), str(dest))
                    moved_count += 1
            except Exception as e:
                print(f"Error moving {file}: {e}")
        
        print(f"Moved {moved_count} files to {version_dir}")

if __name__ == "__main__":
    organize_gemini_responses()
