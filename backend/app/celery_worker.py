import asyncio
import logging
from celery import Celery
from datetime import timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "chatcore",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def crawl_website_task(self, site_id: int, business_id: int, url: str, config: dict | None = None):
    import asyncio
    from app.services.crawler import CrawlerConfig, CrawlerService
    from app.services.chunker import ChunkerService
    from app.services.vector_store import VectorStoreService
    from app.services.rag import RAGService
    from app.db.session import async_session_factory
    from app.models.website import Website
    from app.models.analytics_event import AnalyticsEvent
    from sqlalchemy import select

    logger.info(f"Starting crawl task for site {site_id}: {url}")

    cfg = config or {}
    crawler_cfg = CrawlerConfig(
        base_url=url,
        max_pages=cfg.get("max_pages", 100),
        max_depth=cfg.get("max_depth", 5),
        sitemap_urls=cfg.get("sitemap_urls", []),
        use_playwright=cfg.get("use_playwright", False),
        auth_token=cfg.get("auth_token"),
        auth_type=cfg.get("auth_type"),
    )

    async def run_crawl():
        crawler = CrawlerService(crawler_cfg)
        result = await crawler.crawl()

        chunker = ChunkerService()
        vector_store = VectorStoreService()
        rag = RAGService()

        total_chunks = 0
        for page in result.pages:
            chunks = chunker.chunk_text(page["content"], page.get("metadata", {}))
            total_chunks += len(chunks)
            await vector_store.upsert_chunks(site_id, chunks)

        self.update_state(
            state="PROGRESS",
            meta={"pages": len(result.pages), "chunks": total_chunks},
        )

        async with async_session_factory() as db:
            from sqlalchemy import select
            stmt = select(Website).where(Website.id == site_id)
            site_result = await db.execute(stmt)
            site = site_result.scalar_one_or_none()
            if site:
                from datetime import datetime, timezone
                site.status = result.status.value
                site.last_crawled_at = datetime.now(timezone.utc)
                await db.flush()

            event = AnalyticsEvent(
                business_id=business_id,
                event_type="crawl",
                properties={
                    "site_id": site_id,
                    "url": url,
                    "pages_count": len(result.pages),
                    "chunks_count": total_chunks,
                    "status": result.status.value,
                    "duration_seconds": result.duration_seconds,
                },
            )
            db.add(event)
            await db.flush()

        return {"pages": len(result.pages), "chunks": total_chunks, "status": result.status.value}

    try:
        return run_async(run_crawl())
    except Exception as exc:
        logger.error(f"Crawl task failed for site {site_id}: {exc}", exc_info=True)
        self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def embed_chunks_task(self, site_id: int, chunks: list[dict]):
    import asyncio
    from app.services.vector_store import VectorStoreService

    logger.info(f"Embedding {len(chunks)} chunks for site {site_id}")

    async def run_embed():
        vs = VectorStoreService()
        await vs.upsert_chunks(site_id, chunks)
        return {"site_id": site_id, "chunks_embedded": len(chunks)}

    try:
        return run_async(run_embed())
    except Exception as exc:
        logger.error(f"Embed task failed for site {site_id}: {exc}")
        self.retry(exc=exc)


@celery_app.task(bind=True)
def recrawl_all_sites_task(self):
    import asyncio
    from app.db.session import async_session_factory
    from app.models.website import Website
    from sqlalchemy import select
    from datetime import datetime, timezone, timedelta

    async def run_recrawl():
        async with async_session_factory() as db:
            result = await db.execute(
                select(Website).where(
                    Website.status == "active",
                )
            )
            sites = result.scalars().all()
            for site in sites:
                if site.last_crawled_at:
                    next_crawl = site.last_crawled_at + timedelta(hours=site.crawl_interval_hours)
                    if datetime.now(timezone.utc) >= next_crawl:
                        crawl_website_task.delay(site.id, site.business_id, site.url)
                else:
                    crawl_website_task.delay(site.id, site.business_id, site.url)
        return {"sites_checked": len(sites)}

    try:
        return run_async(run_recrawl())
    except Exception as exc:
        logger.error(f"Recrawl all task failed: {exc}")
        return {"error": str(exc)}


@celery_app.task
def send_email_task(to: str, subject: str, body: str):
    from app.services.email_service import EmailService
    email_service = EmailService()
    email_service.send(to, subject, body)
    return {"to": to, "subject": subject}


@celery_app.task
def generate_suggestions_task(site_id: int):
    import asyncio
    from app.services.rag import RAGService
    async def run():
        rag = RAGService()
        questions = await rag.generate_suggested_questions(site_id)
        return {"site_id": site_id, "suggestions": questions}
    try:
        return run_async(run())
    except Exception as exc:
        logger.error(f"Generate suggestions failed: {exc}")
        return {"error": str(exc)}


celery_app.conf.beat_schedule = {
    "recrawl-all-sites-every-6-hours": {
        "task": "app.celery_worker.recrawl_all_sites_task",
        "schedule": timedelta(hours=6),
    },
}
