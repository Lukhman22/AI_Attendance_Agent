import sys
from pathlib import Path
import getpass

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.database.session import SessionLocal
from backend.app.auth.service import create_user
from backend.app.auth.schemas import UserCreate
from backend.app.auth.permissions import Roles

def main():
    print("Create Admin User")
    print("-" * 20)
    
    email = input("Email: ")
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    
    if not email or not username or not password:
        print("All fields are required!")
        return
        
    db = SessionLocal()
    try:
        user = create_user(db, UserCreate(
            email=email,
            username=username,
            password=password,
            role=Roles.ADMIN
        ))
        print(f"\nAdmin user '{user.username}' created successfully!")
    except Exception as e:
        print(f"\nFailed to create admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
