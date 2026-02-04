from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# MongoDB setup
mongodb_client: AsyncIOMotorClient = None

async def connect_mongo():
    """Connect to MongoDB."""
    global mongodb_client
    mongodb_client = AsyncIOMotorClient(settings.MONGODB_URI)
    # Verify connection
    await mongodb_client.admin.command('ping')
    print("MongoDB connected successfully")

async def close_mongo():
    """Close MongoDB connection."""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("MongoDB connection closed")

def get_mongodb():
    """Get MongoDB client."""
    return mongodb_client

def get_database(db_name: str = None):
    """Get MongoDB database instance."""
    db_name = db_name or settings.MONGODB_DB_NAME
    return mongodb_client[db_name]
