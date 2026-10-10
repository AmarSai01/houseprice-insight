"""
Script to delete all .pkl model files.
"""

import os
import glob

def delete_pkl_files():
    """Delete all .pkl files in the backend directory (excluding venv)."""
    deleted = []
    
    # Search for .pkl files in backend directory
    patterns = [
        "ml/*.pkl",
        "backend/ml/*.pkl",
        "**/*.pkl"
    ]
    
    for pattern in patterns:
        files = glob.glob(pattern, recursive=True)
        for file in files:
            # Skip venv files
            if "venv" not in file and "site-packages" not in file:
                try:
                    os.remove(file)
                    deleted.append(file)
                    print(f"✅ Deleted: {file}")
                except Exception as e:
                    print(f"❌ Could not delete {file}: {e}")
    
    if deleted:
        print(f"\n✅ Deleted {len(deleted)} .pkl file(s)")
    else:
        print("\nℹ️  No .pkl files found to delete")
    
    print("\n💡 To recreate the model files, run:")
    print("   python -m ml.train ../data/house_data.csv")

if __name__ == "__main__":
    delete_pkl_files()





