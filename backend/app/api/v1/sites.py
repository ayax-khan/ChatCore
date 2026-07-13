import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.website import Website

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sites", tags=["sites"])


class SiteCreate(BaseModel):
    url: str
    name: str
    crawl_interval_hours: int = 24


class SiteUpdate(BaseModel):
    name: str | None = None
    url: str | None = None
    crawl_interval_hours: int | None = None


class CrawlConfig(BaseModel):
    sitemap_url: str | None = None
    use_playwright: bool = False
    max_pages: int = 100
    max_depth: int = 5
    rate_limit_delay: float = 0.5
    auth_type: str | None = None
    auth_token: str | None = None


@router.get("/")
async def list_sites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.business_id == current_user.business_id)
    )
    return result.scalars().all()


@router.post("/", status_code=201)
async def create_site(
    req: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Website).where(Website.url == req.url, Website.business_id == current_user.business_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Site URL already exists")

    site = Website(
        business_id=current_user.business_id,
        url=req.url,
        name=req.name,
        crawl_interval_hours=req.crawl_interval_hours,
        status="pending",
    )
    db.add(site)
    await db.flush()

    try:
        await trigger_crawl_logic(site, max_pages=20, use_playwright=False, db=db)
    except Exception as e:
        logger.warning(f"Initial crawl failed for site {site.id}: {e}")
        site.status = "active"

    return {"site_id": site.id, "site_name": site.name, "url": site.url, "status": site.status}


@router.get("/{site_id}")
async def get_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site


@router.patch("/{site_id}")
async def update_site(
    site_id: int,
    req: SiteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    if req.name is not None:
        site.name = req.name
    if req.url is not None:
        site.url = req.url
    if req.crawl_interval_hours is not None:
        site.crawl_interval_hours = req.crawl_interval_hours
    await db.flush()
    return {"site_id": site.id, "name": site.name, "url": site.url, "status": site.status}


@router.delete("/{site_id}")
async def delete_site(
    site_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from app.services.vector_store import VectorStoreService
    vector_store = VectorStoreService()
    await vector_store.delete_site_data(site.id)

    await db.delete(site)
    await db.flush()
    return {"detail": "Site deleted"}


@router.post("/{site_id}/crawl")
async def crawl_site(
    site_id: int,
    config: CrawlConfig = CrawlConfig(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    site.status = "running"
    await db.flush()

    try:
        await trigger_crawl_logic(
            site,
            max_pages=config.max_pages,
            max_depth=config.max_depth,
            sitemap_url=config.sitemap_url,
            use_playwright=config.use_playwright,
            auth_type=config.auth_type,
            auth_token=config.auth_token,
            db=db,
        )

        site.last_crawled_at = datetime.now(timezone.utc)
        site.status = "active"
        await db.flush()

        return {"site_id": site.id, "status": "active", "detail": "Crawl completed"}
    except Exception as e:
        site.status = "failed"
        await db.flush()
        logger.error(f"Crawl failed for site {site_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Crawl failed: {str(e)}")


@router.post("/{site_id}/re-crawl")
async def recrawl_site(
    site_id: int,
    config: CrawlConfig = CrawlConfig(),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    try:
        await db.delete(site)
        await db.flush()

        new_site = Website(
            business_id=site.business_id,
            url=site.url,
            name=site.name,
            crawl_interval_hours=site.crawl_interval_hours
        )
        db.add(new_site)
        await db.flush()

        await trigger_crawl_logic(
            new_site,
            max_pages=config.max_pages,
            max_depth=config.max_depth,
            use_playwright=config.use_playwright,
            db=db,
        )

        new_site.last_crawled_at = datetime.now(timezone.utc)
        new_site.status = "active"
        await db.flush()
        return {"site_id": new_site.id, "status": "active", "detail": "Site re-crawled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Re-crawl failed: {str(e)}")


@router.get("/{site_id}/history")
async def get_site_history(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Website).where(Website.id == site_id, Website.business_id == current_user.business_id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from app.models.analytics_event import AnalyticsEvent
    ev_result = await db.execute(
        select(AnalyticsEvent)
        .where(
            AnalyticsEvent.business_id == current_user.business_id,
            AnalyticsEvent.event_type == "crawl",
            AnalyticsEvent.properties["site_id"].as_string() == str(site_id),
        )
        .order_by(AnalyticsEvent.created_at.desc())
        .limit(20)
    )
    events = ev_result.scalars().all()
    return [
        {
            "date": str(e.created_at) if e.created_at else None,
            "pages_count": e.properties.get("pages_count", 0),
            "duration": e.properties.get("duration_second", 0),
            "status": e.properties.get("status", "unknown"),
        }
        for e in events
    ]


async def trigger_crawl_logic(
    site: Website,
    max_pages: int = 100,
    max_depth: int = 5,
    sitemap_url: str | None = None,
    use_playwright: bool = False,
    auth_type: str | None = None,
    auth_token: str | None = None,
    db: AsyncSession | None = None,
):
    from app.services.crawler import CrawlerConfig, CrawlerService
    from app.services.chunker import ChunkerService
    from app.services.vector_store import VectorStoreService
    from app.services.rag import RAGService

    sitemap_list = [sitemap_url] if sitemap_url else []

    config = CrawlerConfig(
        base_url=site.url,
        max_pages=max_pages,
        max_depth=max_depth,
        rate_limit_delay=0.5,
        use_playwright=use_playwright,
        auth_type=auth_type,
        auth_token=auth_token,
        sitemap_urls=sitemap_list,
    )

    crawler = CrawlerService(config)
    result = await crawler.crawl()

    chunker = ChunkerService(chunk_size=500, chunk_overlap=75)
    vector_store = VectorStoreService()
    rag = RAGService()

    total_chunks = 0
    for page in result.pages:
        chunks = chunker.chunk_text(page["content"], page.get("metadata", {}))
        total_chunks += len(chunks)
        await vector_store.upsert_chunks(site.id, chunks)

    if db is None:
        from app.db.session import async_session_factory
        async with async_session_factory() as session:
            await _log_crawl_event(session, site, result, total_chunks)
    else:
        await _log_crawl_event(db, site, result, total_chunks)

    logger.info(f"Crawled {len(result.pages)} pages, {total_chunks} chunks for site {site.id}")

    return result


async def _log_crawl_event(db: AsyncSession, site: Website, result, total_chunks: int):
    from app.models.analytics_event import AnalyticsEvent
    event = AnalyticsEvent(
        business_id=site.business_id,
        event_type="crawl",
        properties={
            "site_id": site.id,
            "pages_count": len(result.pages),
            "chunks_count": total_chunks,
            "duration_second": result.duration_seconds,
            "status": result.status.value
        }
    )
    db.add(event)
    await db.flush()
