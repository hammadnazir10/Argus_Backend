from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.db.base import Base

# PostgreSQL async engine and session
engine = None
AsyncSessionLocal = None

async def init_database():
    """Initialize database - create all tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Error creating database tables: {e}")
        raise

async def connect_db():
    """Connect to PostgreSQL database and initialize."""
    global engine, AsyncSessionLocal
    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        AsyncSessionLocal = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        # Initialize database - create all tables
        await init_database()
        print("✓ PostgreSQL connected successfully")
    except Exception as e:
        print(f"✗ Error connecting to PostgreSQL: {e}")
        raise

async def close_db():
    """Close PostgreSQL connection."""
    global engine
    if engine:
        await engine.dispose()
        print("PostgreSQL connection closed")

async def get_database() -> AsyncSession:
    """Get database session for dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
