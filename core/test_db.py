import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
async def main():
    client = AsyncIOMotorClient(os.getenv("DATABASE_URL"))
    db = client.brevio
    user = await db.users.find_one({"username": "Darelsm2"})
    if user:
        print("User state:", user.get("plan_id"), user.get("stripe_subscription_status"), user.get("stripe_subscription_id"), user.get("stripe_customer_id"))
    else:
        print("User not found")
asyncio.run(main())
