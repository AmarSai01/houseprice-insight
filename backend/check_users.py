"""
Script to check users in the database.
Run this to see if users are being saved.
"""

from database import SessionLocal, init_db
from models import User

def check_users():
    """Check all users in the database."""
    init_db()
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        print(f"\n=== Users in Database ===")
        print(f"Total users: {len(users)}")
        
        if len(users) == 0:
            print("No users found in database!")
            print("Try registering a user through the frontend or create an admin user.")
        else:
            for user in users:
                print(f"\nUser ID: {user.id}")
                print(f"  Name: {user.name}")
                print(f"  Email: {user.email}")
                print(f"  Role: {user.role}")
                print(f"  Created: {user.created_at}")
        
    except Exception as e:
        print(f"Error checking users: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_users()





