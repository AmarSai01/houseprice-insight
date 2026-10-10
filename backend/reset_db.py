"""
Script to reset the database (delete and recreate).
Use this if you want to start fresh.
"""

import os
from database import engine, Base

def reset_database():
    """Delete database file and recreate tables."""
    db_file = "house_prediction.db"
    
    # Delete database file if it exists
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"✅ Deleted {db_file}")
    
    # Recreate all tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database recreated successfully")
    print("   Run 'python create_admin.py <email> <password>' to create an admin user")

if __name__ == "__main__":
    confirm = input("This will delete all data. Are you sure? (yes/no): ")
    if confirm.lower() == "yes":
        reset_database()
    else:
        print("Cancelled.")





