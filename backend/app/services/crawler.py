import hashlib
import logging
import re
import time
import json
import asyncio
from typing import Optional, Callable
from urllib.parse import urljoin, urlparse, urlencode
from datetime import datetime, timezone
from enum import Enum

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from app.core.config import settings

logger = logging.getLogger(__name__)


class CrawlStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CrawlResult:
    def __init__(self):
        self.pages: list[dict] = []
        self.failed_urls: list[str] = []
        self.skipped_urls: list[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.status: CrawlStatus = CrawlStatus.PENDING

    @property
    def duration_seconds(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def to_dict(self):
        return {
            "pages_count": len(self.pages),
            "failed_count": len(self.failed_urls),
            "skipped_count": len(self.skipped_urls),
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
        }


class CrawlerConfig:
    def __init__(
        self,
        base_url: str,
        max_pages: int = 100,
        max_depth: int = 5,
        same_domain_only: bool = True,
        respect_robots: bool = True,
        rate_limit_delay: float = 0.5,
        max_parallelism: int = 5,
        user_agent: str = "ChatCoreBot/1.0",
        custom_headers: dict | None = None,
        auth_token: str | None = None,
        auth_type: str | None = None,
        use_playwright: bool = False,
        sitemap_urls: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        include_patterns: list[str] | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.same_domain_only = same_domain_only
        self.respect_robots = respect_robots
        self.rate_limit_delay = rate_limit_delay
        self.max_parallelism = max_parallelism
        self.user_agent = user_agent
        self.custom_headers = custom_headers or {}
        self.auth_token = auth_token
        self.auth_type = auth_type
        self.use_playwright = use_playwright
        self.sitemap_urls = sitemap_urls or []
        self.exclude_patterns = exclude_patterns or []
        self.include_patterns = include_patterns or []


class CrawlerService:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited: set[str] = set()
        self.domain = urlparse(config.base_url).netloc
        self.result = CrawlResult()
        self.sitemap_urls: set[str] = set()
        self.robots_rules: dict[str, list[str]] = {}

    async def crawl(self) -> CrawlResult:
        self.result = CrawlResult()
        self.result.start_time = datetime.now(timezone.utc)
        self.result.status = CrawlStatus.RUNNING

        try:
            if self.config.sitemap_urls or await self._auto_discover_sitemap():
                sitemap_urls = await self._fetch_sitemaps()
                self.sitemap_urls = sitemap_urls

            if self.config.respect_robots:
                await self._fetch_robots_txt()

            seed_urls = self._collect_seed_urls()
            await self._crawl_urls(seed_urls)

            self.result.status = CrawlStatus.COMPLETED
        except Exception as e:
            logger.error(f"Crawl failed: {e}", exc_info=True)
            self.result.status = CrawlStatus.FAILED
        finally:
            self.result.end_time = datetime.now(timezone.utc)

        return self.result

    async def _auto_discover_sitemap(self) -> bool:
        common_paths = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/sitemap/",
            "/sitemap1.xml",
        ]
        for path in common_paths:
            url = self.config.base_url.rstrip("/") + path
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(url, headers=self._headers())
                    if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
                        self.config.sitemap_urls.append(url)
                        logger.info(f"Auto-discovered sitemap: {url}")
                        return True
            except Exception:
                continue
        return False

    async def _fetch_sitemaps(self) -> set[str]:
        urls = set()
        for sitemap_url in self.config.sitemap_urls:
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(sitemap_url, headers=self._headers())
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "xml")
                    for loc in soup.find_all("loc"):
                        url = loc.get_text(strip=True)
                        if url and self._is_allowed_url(url):
                            urls.add(url)
                    for sitemap_loc in soup.find_all("sitemap"):
                        sloc = sitemap_loc.find("loc")
                        if sloc:
                            sub_urls = await self._fetch_sitemap(sloc.get_text(strip=True))
                            urls.update(sub_urls)
            except Exception as e:
                logger.warning(f"Failed to fetch sitemap {sitemap_url}: {e}")
        return urls

    async def _fetch_sitemap(self, sitemap_url: str) -> set[str]:
        urls = set()
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(sitemap_url, headers=self._headers())
                if resp.status_code != 200:
                    return urls
                soup = BeautifulSoup(resp.text, "xml")
                for loc in soup.find_all("loc"):
                    url = loc.get_text(strip=True)
                    if url and self._is_allowed_url(url):
                        urls.add(url)
        except Exception as e:
            logger.warning(f"Failed to fetch sub-sitemap {sitemap_url}: {e}")
        return urls

    async def _fetch_robots_txt(self):
        robots_url = self.config.base_url.rstrip("/") + "/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(robots_url, headers=self._headers())
                if resp.status_code != 200:
                    return
                lines = resp.text.splitlines()
                current_agent = None
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("user-agent"):
                        agent = line.split(":", 1)[1].strip()
                        if agent == "*" or agent.lower() == self.config.user_agent.lower():
                            current_agent = agent
                        else:
                            current_agent = None
                    elif line.lower().startswith("disallow") and current_agent:
                        path = line.split(":", 1)[1].strip()
                        if path:
                            full_url = urljoin(self.config.base_url, path)
                            self.robots_rules.setdefault(current_agent, []).append(full_url)
                    elif line.lower().startswith("allow") and current_agent:
                        path = line.split(":", 1)[1].strip()
                        if path:
                            full_url = urljoin(self.config.base_url, path)
                            self.robots_rules.setdefault(current_agent, []).append(full_url)
                    elif line.lower().startswith("crawl-delay") and current_agent:
                        delay = float(line.split(":", 1)[1].strip())
                        self.config.rate_limit_delay = delay
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt: {e}")

    def _is_allowed_by_robots(self, url: str) -> bool:
        if not self.config.respect_robots:
            return True
        for agent, rules in self.robots_rules.items():
            for rule in rules:
                allowed = rule in url and rule
                if allowed:
                    return True
        return True

    def _is_excluded_url(self, url: str) -> bool:
        for pattern in self.config.exclude_patterns:
            if re.search(pattern, url):
                return True
        return False

    def _is_included_url(self, url: str) -> bool:
        if not self.config.include_patterns:
            return True
        for pattern in self.config.include_patterns:
            if re.search(pattern, url):
                return True
        return False

    def _is_allowed_url(self, url: str) -> bool:
        if not self.config.same_domain_only:
            pass
        elif urlparse(url).netloc != self.domain:
            return False
        if self._is_excluded_url(url):
            return False
        if not self._is_included_url(url):
            return False
        if not self._is_allowed_by_robots(url):
            return False
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        ext = parsed.path.split(".")[-1].lower() if "." in parsed.path else ""
        excluded_exts = {"jpg", "jpeg", "png", "gif", "svg", "ico", "css", "js", "mp3", "mp4", "avi", "mov", "zip", "gz", "tar", "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"}
        if ext in excluded_exts and ext != "" and len(ext) <= 5:
            return False
        excluded_paths = ["/login", "/logout", "/signup", "/register", "/admin", "/cart", "/checkout", "/search", "/tag", "/category"]
        if any(p in parsed.path.lower() for p in excluded_paths):
            return False
        return True

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") if parsed.path else "/"
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _headers(self) -> dict:
        headers = {
            "User-Agent": self.config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        if self.config.auth_token and self.config.auth_type:
            if self.config.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.config.auth_token}"
            elif self.config.auth_type == "basic":
                headers["Authorization"] = f"Basic {self.config.auth_token}"
        headers.update(self.config.custom_headers)
        return headers

    def _collect_seed_urls(self) -> list[str]:
        seed_urls = list(self.sitemap_urls)
        if not seed_urls:
            seed_urls.append(self.config.base_url)
        return seed_urls

    async def _crawl_urls(self, seed_urls: list[str]) -> None:
        queue = [(url, 0) for url in seed_urls]
        semaphore = asyncio.Semaphore(self.config.max_parallelism)

        async def process_url(url: str, depth: int):
            if len(self.result.pages) >= self.config.max_pages:
                return
            normalized = self._normalize_url(url)
            if normalized in self.visited or depth > self.config.max_depth:
                return
            self.visited.add(normalized)

            async with semaphore:
                page = await self._fetch_and_process(normalized)
                if page:
                    self.result.pages.append(page)

                await asyncio.sleep(self.config.rate_limit_delay)

                links = page.get("_links", []) if page else []
                return [(link, depth + 1) for link in links]

        tasks = []
        for url, depth in queue:
            if len(self.result.pages) >= self.config.max_pages:
                break
            task = asyncio.ensure_future(process_url(url, depth))
            tasks.append(task)

        while tasks:
            done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                if result:
                    for url, depth in result:
                        if len(self.result.pages) < self.config.max_pages and url not in self.visited:
                            tasks.append(asyncio.ensure_future(process_url(url, depth)))

    async def _fetch_and_process(self, url: str) -> Optional[dict]:
        raw_html = await self._fetch_url(url)
        if not raw_html:
            self.result.failed_urls.append(url)
            return None

        extracted = self._extract_content(raw_html)
        text = self._clean_content(extracted["text"])
        if self._is_low_value_page(text):
            self.result.skipped_urls.append(url)
            return None

        links = self._extract_links(raw_html, url)
        filtered_links = [l for l in links if self._is_allowed_url(l)]
        normalized_links = [self._normalize_url(l) for l in filtered_links]

        language = self._detect_language(text)

        return {
            "url": url,
            "content": text,
            "title": extracted["title"],
            "summary": extracted.get("summary", ""),
            "metadata": {
                "url": url,
                "title": extracted["title"],
                "language": language,
                "detected_language": language,
                "authors": extracted.get("authors", []),
                "published_date": extracted.get("published_date", ""),
                "source_type": "webpage",
            },
            "_links": normalized_links,
        }

    async def _fetch_url(self, url: str) -> Optional[str]:
        if self.config.use_playwright:
            return await self._fetch_with_playwright(url)

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    verify=False,
                ) as client:
                    resp = await client.get(url, headers=self._headers())
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "")
                        if "text" in content_type or "html" in content_type or "xml" in content_type or "json" in content_type:
                            return resp.text
                        if resp.status_code >= 500 and attempt < 2:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        if resp.status_code == 429:
                            await asyncio.sleep(10)
                            continue
                    return resp.text if resp.status_code == 200 else None
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Failed to fetch {url} after 3 attempts: {e}")
                    return None
                await asyncio.sleep(2 ** attempt)
        return None

    async def _fetch_with_playwright(self, url: str) -> Optional[str]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("Playwright not installed, falling back to HTTP fetch")
            return await self._fetch_url(url)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.config.user_agent,
                    viewport={"width": 1920, "height": 1080},
                )
                if self.config.auth_token:
                    context.set_default_timeout(30000)
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            logger.warning(f"Playwright fetch failed for {url}: {e}, falling back to HTTP")
            return await self._fetch_url(url)

    def _extract_content(self, html: str) -> dict:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe", "svg", "canvas"]):
            tag.decompose()
        for tag in soup.find_all(True):
            if tag.name in ("nav", "footer", "header", "aside"):
                tag.decompose()
            if tag.get("class") and any(c in ["sidebar", "menu", "navbar", "footer", "header", "advertisement", "ad", "social", "comments", "comment", "share", "hidden", "modal"] for c in tag.get("class", [])):
                tag.decompose()
            if tag.get("id") and any(c in ["sidebar", "menu", "navbar", "footer", "header", "advertisement", "ad", "social", "comments", "comment", "share", "hidden", "modal"] for c in tag.get("id", [])):
                tag.decompose()
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
        meta_description = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_description = meta_tag.get("content")

        authors = []
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            authors.append(author_meta.get("content"))

        pub_date = ""
        for meta in soup.find_all("meta"):
            if meta.get("property") in ["article:published_time", "article:modified_time"] or meta.get("name") in ["pubdate", "publish-date"] or meta.get("name") == "date":
                pub_date = meta.get("content", "")

        body = soup.find("body") or soup
        for tag in body(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        text = md(str(body), heading_style="ATX", strip=["img", "video", "audio"])

        summary = ""
        if meta_description:
            summary = meta_description
        else:
            first_p = soup.find("p")
            if first_p:
                summary = first_p.get_text(strip=True)[:300]

        return {
            "title": title,
            "text": text,
            "summary": summary,
            "authors": authors,
            "published_date": pub_date,
        }

    def _clean_content(self, text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {3,}", " ", text)
        lines = text.split("\n")
        lines = [l.strip() for l in lines]
        lines = [l for l in lines if l and len(l) > 2]
        return "\n".join(lines)

    def _is_low_value_page(self, text: str) -> bool:
        if len(text) < 20:
            return True
        return False

    def _detect_language(self, text: str) -> str:
        import re
        if not text:
            return "en"
        char_count = len(text)
        if char_count == 0:
            return "en"
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        japanese_chars = len(re.findall(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]", text))
        korean_chars = len(re.findall(r"[\uac00-\ud7af]", text))
        arabic_chars = len(re.findall(r"[\u0600-\u06ff]", text))
        devanagari_chars = len(re.findall(r"[\u0900-\u097f]", text))
        if chinese_chars / char_count > 0.3:
            if japanese_chars > chinese_chars: return "ja"
            if korean_chars > chinese_chars: return "ko"
            return "zh"
        if arabic_chars / char_count > 0.3:
            return "ar"
        if devanagari_chars / char_count > 0.3:
            return "hi"
        return "en"

    def _extract_links(self, html: str, current_url: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            try:
                full_url = urljoin(current_url, href)
                cleaned_url = full_url.split("#")[0].split("?")[0]
                cleaned_url = re.sub(r"(utm_source|utm_medium|utm_campaign|utm_term|utm_content)=[^&]+&?", "", cleaned_url).rstrip("?")
                parsed = urlparse(cleaned_url)
                if parsed.scheme in ("http", "https", ""):
                    if parsed.scheme == "":
                        cleaned_url = urljoin(current_url, cleaned_url)
                    links.append(cleaned_url)
            except Exception:
                continue
        return links


class IncrementalCrawlerService:
    def __init__(self, base_crawler: CrawlerService):
        self.crawler = base_crawler

    async def incremental_crawl(
        self,
        existing_pages: list[dict],
    ) -> tuple[list[dict], list[str], list[str]]:
        new_pages = []
        changed_pages = []
        removed_urls = []

        result = await self.crawler.crawl()

        existing_urls = {p.get("url"): p for p in existing_pages}
        crawled_urls = {p["url"] for p in result.pages if p.get("url")}

        for p in result.pages:
            url = p["url"]
            if url not in existing_urls:
                new_pages.append(p)
            else:
                old_hash = existing_urls[url].get("_hash")
                new_hash = hashlib.md5(p["content"].encode()).hexdigest()
                if old_hash != new_hash:
                    p["_hash"] = new_hash
                    changed_pages.append(p)

        for url in existing_urls:
            if url not in crawled_urls:
                removed_urls.append(url)

        return new_pages, changed_pages, removed_urls