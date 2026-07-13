import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.business import Business
from app.models.user import User
from app.models.plan import Plan
from app.models.website import Website


TEST_DATABASE_URL = "sqlite+aiosqlite://"


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_business(db_session):
    plan = Plan(name="Test Plan", features={"sites": 5, "queries_per_month": 1000}, monthly_fee=0.0)
    db_session.add(plan)
    await db_session.flush()

    business = Business(name="Test Business", plan_id=plan.id)
    db_session.add(business)
    await db_session.flush()
    return business


@pytest_asyncio.fixture
async def test_user(db_session, test_business):
    user = User(
        business_id=test_business.id,
        email="test@example.com",
        hashed_password=get_password_hash("Test123!"),
        role="admin",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_site(db_session, test_business):
    site = Website(
        business_id=test_business.id,
        url="https://example.com",
        name="Test Site",
        status="pending",
    )
    db_session.add(site)
    await db_session.flush()
    return site


@pytest_asyncio.fixture
async def auth_headers(test_user):
    token = create_access_token({
        "sub": str(test_user.id),
        "role": test_user.role,
        "business_id": test_user.business_id,
    })
    return {"Authorization": f"Bearer {token}"}
