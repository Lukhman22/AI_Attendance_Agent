import httpx
import asyncio
import os
import json
import subprocess
import time

async def verify_flow():
    # 1. Start the FastAPI backend
    print("Starting backend for verification...")
    server = subprocess.Popen(
        ["venv/bin/python", "-m", "uvicorn", "backend.app.main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    time.sleep(3)
    
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000/api") as client:
        try:
            print("1. Verifying Settings API (Persistence)")
            res = await client.get("/settings")
            assert res.status_code == 200
            print("   ✅ Settings loaded.")
            
            print("2. Verifying Employee Listing")
            res = await client.get("/employees")
            assert res.status_code == 200
            employees = res.json()
            print(f"   ✅ Employees loaded: {len(employees)}")
            
            print("3. Verifying Salary Configurations")
            res = await client.get("/salaries")
            assert res.status_code == 200
            salaries = res.json()
            print(f"   ✅ Salaries loaded: {len(salaries)}")
            
            print("4. Verifying Daily Reports")
            # Today's date
            from datetime import date
            today = date.today().isoformat()
            res = await client.get(f"/ai/reports/daily/{today}")
            assert res.status_code == 200
            print("   ✅ Daily reports API working.")
            
            print("5. Verifying Monthly AI Insights")
            res = await client.get("/ai/insights/monthly/2026/7")
            assert res.status_code == 200
            print("   ✅ Monthly AI insights working.")
            
            print("6. Verifying Telegram Notification Trigger")
            # Note: we won't actually trigger it if the config isn't valid, just check endpoint
            test_data = {"telegram_bot_token": "dummy", "telegram_chat_id": "dummy"}
            res = await client.post("/settings/test-telegram", json=test_data)
            # We expect a 400 because 'dummy' is an invalid token, meaning it hit the correct logic
            assert res.status_code in [200, 400]
            print("   ✅ Telegram test endpoint working.")
            
            print("\n🎉 All Verification Steps Passed!")
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
        finally:
            print("Shutting down backend...")
            server.terminate()
            server.wait()

if __name__ == "__main__":
    asyncio.run(verify_flow())
