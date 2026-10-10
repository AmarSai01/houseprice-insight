"""
Script to create an admin user.
Run this script to create an admin account.
Usage: python create_admin.py <email> <password> [name]
"""

import sys
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import User
from auth import get_password_hash


def create_admin(email: str, password: str, name: str = "Admin"):
    """Create an admin user."""
    init_db()
    db: Session = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"User with email {email} already exists!")
            if existing_user.role == "admin":
                print("User is already an admin.")
            else:
                existing_user.role = "admin"
                db.commit()
                print(f"Updated user {email} to admin role.")
            return
        
        # Create new admin user
        hashed_password = get_password_hash(password)
        admin_user = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            role="admin"
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {name}")
        print(f"   Role: {admin_user.role}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [name]")
        print("Example: python create_admin.py admin@example.com password123 Admin")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    create_admin(email, password, name)
