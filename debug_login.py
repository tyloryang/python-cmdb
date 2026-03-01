import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.core.security import verify_password
from sqlalchemy import select

async def debug_login():
    try:
        print("Starting debug login...")
        async with AsyncSessionLocal() as db:
            print("Session created. Querying user 'admin'...")
            result = await db.execute(select(User).where(User.username == "admin"))
            user = result.scalar_one_or_none()
            if not user:
                print("Error: User not found!")
                return
            
            print(f"User found: {user.username}")
            
            print("Verifying password...")
            is_valid = verify_password("123456", user.hashed_password)
            print(f"Password valid: {is_valid}")
            
            if is_valid:
                print("Checking if user is active...")
                if not user.is_active:
                    print("Error: User is inactive!")
                    return
                print("Login successful! Token generation would happen next.")
            else:
                print("Login failed! Invalid password.")
            
    except Exception as e:
        import traceback
        print("An error occurred:")
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(debug_login())
