from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.integrations.xiaohongshu_mcp import XiaohongshuMcpClient
from app.models.entities import MediaAsset
from app.services.app_settings import app_settings_service

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional runtime dependency
    PlaywrightTimeoutError = Exception
    sync_playwright = None


@dataclass
class GeneratedAsset:
    asset_type: str
    source_url: str
    local_path: Path
    metadata: dict


class ImageSourceProvider(Protocol):
    provider_name: str

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
    ) -> list[GeneratedAsset]: ...


class MockXiaohongshuSvgProvider:
    provider_name = "mock-xiaohongshu"

    default_tags = [
        "landmark",
        "nature",
        "food",
        "street_scene",
        "hotel",
        "transport",
        "night_view",
        "crowd_level",
    ]

    palette = {
        "landmark": ("#d96c46", "#f7e6d9"),
        "nature": ("#2d6a4f", "#d8f3dc"),
        "food": ("#b56576", "#ffe5ec"),
        "street_scene": ("#355070", "#e9f1ff"),
        "hotel": ("#6d597a", "#f3e8ff"),
        "transport": ("#1d3557", "#dcecff"),
        "night_view": ("#22223b", "#d6d6f5"),
        "crowd_level": ("#bc6c25", "#fff2dd"),
    }

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
    ) -> list[GeneratedAsset]:
        assets: list[GeneratedAsset] = []
        title = article_context.get("title") or destination
        summary = article_context.get("summary") or "Travel visual pack"

        for index in range(1, 11):
            tag = self.default_tags[(index - 1) % len(self.default_tags)]
            image_path = images_dir / f"asset_{index:02d}_{tag}.svg"
            image_path.write_text(
                self._render_image_svg(
                    destination=destination,
                    title=title,
                    summary=summary,
                    tag=tag,
                    index=index,
                ),
                encoding="utf-8",
            )
            assets.append(
                GeneratedAsset(
                    asset_type="image_source",
                    source_url=f"https://www.xiaohongshu.com/explore/mock-{index}",
                    local_path=image_path,
                    metadata={
                        "tag": tag,
                        "provider": self.provider_name,
                        "caption_hint": f"{destination} 图像素材 {index}",
                        "format": "svg",
                        "kind": "generated_vector",
                    },
                )
            )

        return assets

    def _render_image_svg(
        self,
        destination: str,
        title: str,
        summary: str,
        tag: str,
        index: int,
    ) -> str:
        primary, soft = self.palette.get(tag, ("#444", "#efefef"))
        safe_destination = escape(destination)
        safe_title = escape(title[:42])
        safe_summary = escape(summary[:80])
        safe_tag = escape(tag.replace("_", " ").title())
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">
  <defs>
    <linearGradient id="bg{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{soft}" />
      <stop offset="100%" stop-color="#ffffff" />
    </linearGradient>
  </defs>
  <rect width="1200" height="900" fill="url(#bg{index})" />
  <circle cx="1020" cy="180" r="130" fill="{primary}" opacity="0.15" />
  <circle cx="180" cy="730" r="170" fill="{primary}" opacity="0.12" />
  <rect x="86" y="88" width="1028" height="724" rx="34" fill="white" opacity="0.72" />
  <text x="120" y="170" fill="{primary}" font-size="28" font-family="Georgia, serif" letter-spacing="4">TRAVEL IMAGE {index:02d}</text>
  <text x="120" y="260" fill="#1b1b1b" font-size="64" font-family="Georgia, serif">{safe_destination}</text>
  <text x="120" y="332" fill="#5b5b5b" font-size="32" font-family="Georgia, serif">{safe_tag}</text>
  <text x="120" y="430" fill="#2d2d2d" font-size="40" font-family="Georgia, serif">{safe_title}</text>
  <foreignObject x="120" y="490" width="900" height="170">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: Georgia, serif; color:#444; font-size:28px; line-height:1.5;">
      {safe_summary}
    </div>
  </foreignObject>
  <rect x="120" y="720" width="220" height="54" rx="27" fill="{primary}" />
  <text x="155" y="756" fill="white" font-size="24" font-family="Georgia, serif">#{safe_tag}</text>
</svg>
"""


class DemoRemotePhotoProvider:
    provider_name = "demo-remote-photo"

    default_tags = [
        "landmark",
        "nature",
        "food",
        "street_scene",
        "hotel",
        "transport",
        "night_view",
        "crowd_level",
    ]

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
    ) -> list[GeneratedAsset]:
        assets: list[GeneratedAsset] = []
        summary = article_context.get("summary") or destination
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            for index in range(1, 11):
                tag = self.default_tags[(index - 1) % len(self.default_tags)]
                source_url = (
                    "https://picsum.photos/seed/"
                    f"{article_job_id}-{tag}-{index}/1200/900"
                )
                response = client.get(source_url)
                response.raise_for_status()
                image_path = images_dir / f"asset_{index:02d}_{tag}.jpg"
                image_path.write_bytes(response.content)
                assets.append(
                    GeneratedAsset(
                        asset_type="image_source",
                        source_url=str(response.url),
                        local_path=image_path,
                        metadata={
                            "tag": tag,
                            "provider": self.provider_name,
                            "caption_hint": f"{destination} {tag} 参考图",
                            "format": "jpg",
                            "kind": "downloaded_demo_photo",
                            "summary_hint": summary[:100],
                        },
                    )
                )
        return assets


class ExternalUrlIngestProvider:
    provider_name = "external-url-ingest"

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
        manifest: list[dict],
    ) -> list[GeneratedAsset]:
        assets: list[GeneratedAsset] = []
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for index, item in enumerate(manifest, start=1):
                if not isinstance(item, dict) or not item.get("url"):
                    continue
                tag = str(item.get("tag") or "landmark")
                response = client.get(str(item["url"]))
                response.raise_for_status()
                suffix = self._infer_suffix(str(response.url))
                image_path = images_dir / f"asset_{index:02d}_{tag}{suffix}"
                image_path.write_bytes(response.content)
                assets.append(
                    GeneratedAsset(
                        asset_type="image_source",
                        source_url=str(item["url"]),
                        local_path=image_path,
                        metadata={
                            "tag": tag,
                            "provider": self.provider_name,
                            "title": str(item.get("title") or ""),
                            "source_page": str(item.get("source_page") or ""),
                            "format": suffix.lstrip("."),
                            "kind": "external_url_download",
                            "caption_hint": f"{destination} {tag} 导入图",
                        },
                    )
                )
        return assets

    def _infer_suffix(self, url: str) -> str:
        path = urlparse(url).path.lower()
        for suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if path.endswith(suffix):
                return suffix
        return ".jpg"


class XiaohongshuNoteScrapeProvider:
    provider_name = "xiaohongshu-note-scrape"

    default_tag_order = [
        "landmark",
        "nature",
        "food",
        "street_scene",
        "hotel",
        "transport",
        "night_view",
        "crowd_level",
    ]

    tag_keywords = {
        "food": ["美食", "小吃", "咖啡", "火锅", "早餐", "餐厅", "夜宵", "甜品"],
        "hotel": ["酒店", "民宿", "住宿", "客栈", "房间"],
        "transport": ["地铁", "高铁", "火车", "公交", "自驾", "机场", "交通"],
        "night_view": ["夜景", "日落", "晚霞", "夜游", "灯光"],
        "nature": ["山", "湖", "海", "森林", "公园", "花海", "草原", "瀑布"],
        "street_scene": ["citywalk", "街区", "街景", "老街", "巷子", "市集"],
        "landmark": ["地标", "塔", "古城", "博物馆", "寺", "桥", "景点"],
        "crowd_level": ["人少", "避坑", "小众", "冷门", "排队"],
    }

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
        seed_urls: list[str],
    ) -> list[GeneratedAsset]:
        preview = self.preview(
            seed_urls,
            destination=destination,
            article_context=article_context,
        )
        assets: list[GeneratedAsset] = []
        with httpx.Client(timeout=30, follow_redirects=True, headers=self._headers()) as client:
            for index, image in enumerate(preview["images"][:10], start=1):
                image_url = str(image.get("image_url") or "")
                if not image_url:
                    continue
                response = client.get(image_url)
                response.raise_for_status()
                tag = str(image.get("tag") or self.default_tag_order[(index - 1) % len(self.default_tag_order)])
                suffix = self._infer_suffix(str(response.url))
                image_path = images_dir / f"asset_{index:02d}_{tag}{suffix}"
                image_path.write_bytes(response.content)
                assets.append(
                    GeneratedAsset(
                        asset_type="image_source",
                        source_url=image_url,
                        local_path=image_path,
                        metadata={
                            "tag": tag,
                            "provider": self.provider_name,
                            "title": str(image.get("note_title") or ""),
                            "source_page": str(image.get("source_page") or ""),
                            "format": suffix.lstrip("."),
                            "kind": "xiaohongshu_public_page_image",
                            "caption_hint": f"{destination} {tag} 小红书素材",
                            "note_index": image.get("note_index", 0),
                        },
                    )
                )
        return assets

    def preview(
        self,
        seed_urls: list[str],
        *,
        destination: str = "",
        article_context: dict | None = None,
        limit: int = 8,
    ) -> dict:
        normalized_urls = [item.strip() for item in seed_urls if item.strip()]
        discovered_urls: list[str] = []
        browser_diagnostics: dict = {
            "enabled": sync_playwright is not None,
            "attempted": False,
            "blocked": False,
            "error_code": "",
            "error_message": "",
            "final_url": "",
        }
        if not normalized_urls:
            discovered_urls, browser_diagnostics = self.discover_seed_urls(
                destination=destination,
                article_context=article_context or {},
                limit=limit,
            )
            normalized_urls = discovered_urls
        notes: list[dict] = []
        flattened_images: list[dict] = []
        with httpx.Client(timeout=20, follow_redirects=True, headers=self._headers()) as client:
            for note_index, url in enumerate(normalized_urls, start=1):
                try:
                    response = client.get(url)
                    response.raise_for_status()
                    html = response.text
                    extracted = self._extract_note_payload(str(response.url), html, note_index)
                    if not extracted["images"]:
                        browser_extracted = self._extract_note_payload_via_browser(
                            str(response.url),
                            note_index,
                        )
                        if browser_extracted["images"]:
                            extracted = browser_extracted
                    notes.append(extracted)
                    flattened_images.extend(extracted["images"])
                except Exception as exc:
                    browser_extracted = self._extract_note_payload_via_browser(url, note_index)
                    if browser_extracted["images"]:
                        notes.append(browser_extracted)
                        flattened_images.extend(browser_extracted["images"])
                    else:
                        notes.append(
                            {
                                "source_page": url,
                                "note_title": "",
                                "note_description": "",
                                "images": [],
                                "error": str(exc),
                                "note_index": note_index,
                            }
                        )
        return {
            "provider": self.provider_name,
            "discovery_mode": not bool(seed_urls),
            "discovered_seed_urls": discovered_urls,
            "seed_count": len(normalized_urls),
            "note_count": len(notes),
            "image_count": len(flattened_images),
            "browser_diagnostics": browser_diagnostics,
            "notes": notes,
            "images": flattened_images,
        }

    def discover_seed_urls(
        self,
        *,
        destination: str,
        article_context: dict,
        limit: int = 8,
    ) -> tuple[list[str], dict]:
        diagnostics = {
            "enabled": sync_playwright is not None,
            "attempted": False,
            "blocked": False,
            "error_code": "",
            "error_message": "",
            "final_url": "",
        }
        browser_discovered = self._discover_seed_urls_via_browser(
            destination=destination,
            article_context=article_context,
            limit=limit,
        )
        if browser_discovered["urls"]:
            return browser_discovered["urls"], browser_discovered["diagnostics"]
        diagnostics = browser_discovered["diagnostics"]

        queries = self._build_discovery_queries(destination, article_context)
        discovered: list[str] = []
        seen: set[str] = set()
        with httpx.Client(timeout=20, follow_redirects=True, headers=self._headers()) as client:
            for query in queries:
                if len(discovered) >= limit:
                    break
                urls: list[str] = []
                for search_fn in (self._search_bing_rss, self._search_bing, self._search_duckduckgo):
                    try:
                        urls = search_fn(client, query)
                    except Exception:
                        urls = []
                    if urls:
                        break
                for url in urls:
                    normalized = self._normalize_note_url(url)
                    if not normalized or normalized in seen:
                        continue
                    seen.add(normalized)
                    discovered.append(normalized)
                    if len(discovered) >= limit:
                        break
        return discovered, diagnostics

    def _build_discovery_queries(self, destination: str, article_context: dict) -> list[str]:
        title = str(article_context.get("title") or "").strip()
        summary = str(article_context.get("summary") or "").strip()
        base = destination.strip() or title or summary or "旅行攻略"
        candidates = [
            f"site:xiaohongshu.com {base} 攻略",
            f"site:xiaohongshu.com {base} citywalk",
            f"site:xiaohongshu.com {base} 美食",
            f"site:xiaohongshu.com {base} 酒店",
            f"site:xiaohongshu.com {base} 夜景",
        ]
        if title:
            candidates.append(f"site:xiaohongshu.com {title}")
        return candidates

    def _discover_seed_urls_via_browser(
        self,
        *,
        destination: str,
        article_context: dict,
        limit: int,
    ) -> dict:
        diagnostics = {
            "enabled": sync_playwright is not None,
            "attempted": sync_playwright is not None,
            "blocked": False,
            "error_code": "",
            "error_message": "",
            "final_url": "",
        }
        if sync_playwright is None:
            return {"urls": [], "diagnostics": diagnostics}

        keyword = (
            destination.strip()
            or str(article_context.get("title") or "").strip()
            or str(article_context.get("summary") or "").strip()
            or "旅行攻略"
        )
        seen: set[str] = set()
        discovered: list[str] = []
        search_url = f"https://www.xiaohongshu.com/search_result/?keyword={quote_plus(keyword)}"
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self._headers()["User-Agent"],
                    locale="zh-CN",
                    viewport={"width": 1440, "height": 1200},
                )
                page = context.new_page()
                page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4500)
                try:
                    page.wait_for_url("**/website-login/error**", timeout=2500)
                except Exception:
                    pass
                diagnostics["final_url"] = page.url
                if self._mark_browser_block_if_needed(page, diagnostics):
                    context.close()
                    browser.close()
                    return {"urls": [], "diagnostics": diagnostics}
                for _ in range(3):
                    hrefs = page.eval_on_selector_all(
                        "a",
                        """(nodes) => nodes
                          .map((node) => node.href || node.getAttribute('href') || '')
                          .filter(Boolean)""",
                    )
                    for href in hrefs:
                        normalized = self._normalize_note_url(str(href))
                        if not normalized or normalized in seen:
                            continue
                        seen.add(normalized)
                        discovered.append(normalized)
                        if len(discovered) >= limit:
                            break
                    if len(discovered) >= limit:
                        break
                    page.mouse.wheel(0, 1800)
                    page.wait_for_timeout(1800)
                    diagnostics["final_url"] = page.url
                    if self._mark_browser_block_if_needed(page, diagnostics):
                        break
                context.close()
                browser.close()
        except PlaywrightTimeoutError:
            diagnostics["error_message"] = "playwright_timeout"
            return {"urls": discovered[:limit], "diagnostics": diagnostics}
        except Exception as exc:
            diagnostics["error_message"] = str(exc)
            return {"urls": discovered[:limit], "diagnostics": diagnostics}
        return {"urls": discovered[:limit], "diagnostics": diagnostics}

    def _mark_browser_block_if_needed(self, page, diagnostics: dict) -> bool:
        if "/website-login/error" not in page.url:
            return False
        body_text = page.locator("body").inner_text()
        diagnostics["blocked"] = True
        diagnostics["final_url"] = page.url
        code_match = re.search(r"\b(300\d{3})\b", body_text)
        diagnostics["error_code"] = code_match.group(1) if code_match else ""
        diagnostics["error_message"] = body_text[:300]
        return True

    def _search_duckduckgo(self, client: httpx.Client, query: str) -> list[str]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        response = client.get(url)
        response.raise_for_status()
        html = response.text
        hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
        candidates: list[str] = []
        for href in hrefs:
            resolved = self._resolve_search_href(href)
            if resolved and "xiaohongshu.com" in resolved:
                candidates.append(resolved)
        return candidates

    def _search_bing_rss(self, client: httpx.Client, query: str) -> list[str]:
        response = client.get("https://cn.bing.com/search", params={"format": "rss", "q": query})
        response.raise_for_status()
        xml = response.text
        links = re.findall(r"<link>(https?://[^<]+)</link>", xml, flags=re.IGNORECASE)
        return [
            link
            for link in links
            if "xiaohongshu.com" in link and self._normalize_note_url(link)
        ]

    def _search_bing(self, client: httpx.Client, query: str) -> list[str]:
        url = f"https://www.bing.com/search?q={quote_plus(query)}"
        response = client.get(url)
        response.raise_for_status()
        html = response.text
        hrefs = re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
        candidates: list[str] = []
        for href in hrefs:
            if href.startswith("http") and "xiaohongshu.com" in href:
                candidates.append(href)
        return candidates

    def _resolve_search_href(self, href: str) -> str:
        if href.startswith("//"):
            return f"https:{href}"
        if href.startswith("http"):
            return href
        if "uddg=" in href:
            parsed = urlparse(href)
            uddg = parse_qs(parsed.query).get("uddg", [])
            if uddg:
                return unquote(uddg[0])
        return ""

    def _normalize_note_url(self, url: str) -> str:
        parsed = urlparse(url)
        if "xiaohongshu.com" not in parsed.netloc:
            return ""
        if not (
            parsed.path.startswith("/explore/")
            or parsed.path.startswith("/discovery/item/")
        ):
            return ""
        return f"https://{parsed.netloc}{parsed.path}"

    def _extract_note_payload(self, source_page: str, html: str, note_index: int) -> dict:
        title = self._extract_first_meta(html, ["og:title", "twitter:title"]) or self._extract_title_tag(html)
        description = self._extract_first_meta(
            html,
            ["og:description", "description", "twitter:description"],
        )
        image_urls = self._extract_image_urls(html)
        images: list[dict] = []
        for image_index, image_url in enumerate(image_urls, start=1):
            tag = self._guess_tag(title, description, source_page, image_index)
            images.append(
                {
                    "image_url": image_url,
                    "tag": tag,
                    "source_page": source_page,
                    "note_title": title,
                    "note_description": description,
                    "note_index": note_index,
                    "image_index": image_index,
                }
            )
        return {
            "source_page": source_page,
            "note_title": title,
            "note_description": description,
            "images": images,
            "note_index": note_index,
        }

    def _extract_note_payload_via_browser(self, source_page: str, note_index: int) -> dict:
        if sync_playwright is None:
            return {
                "source_page": source_page,
                "note_title": "",
                "note_description": "",
                "images": [],
                "note_index": note_index,
                "error": "playwright_unavailable",
            }

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=self._headers()["User-Agent"],
                    locale="zh-CN",
                    viewport={"width": 1440, "height": 1200},
                )
                page = context.new_page()
                page.goto(source_page, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)
                payload = page.evaluate(
                    """() => {
                      const title =
                        document.querySelector('meta[property="og:title"]')?.content ||
                        document.querySelector('meta[name="twitter:title"]')?.content ||
                        document.title ||
                        '';
                      const description =
                        document.querySelector('meta[property="og:description"]')?.content ||
                        document.querySelector('meta[name="description"]')?.content ||
                        document.querySelector('meta[name="twitter:description"]')?.content ||
                        '';
                      const candidates = new Set();
                      document.querySelectorAll('meta[property="og:image"], meta[name="twitter:image"]').forEach((node) => {
                        const value = node.getAttribute('content') || '';
                        if (value.startsWith('http')) candidates.add(value);
                      });
                      document.querySelectorAll('img').forEach((img) => {
                        const value = img.currentSrc || img.src || '';
                        if (value.startsWith('http')) candidates.add(value);
                      });
                      return {
                        title,
                        description,
                        imageUrls: Array.from(candidates),
                      };
                    }"""
                )
                context.close()
                browser.close()
        except Exception as exc:
            return {
                "source_page": source_page,
                "note_title": "",
                "note_description": "",
                "images": [],
                "note_index": note_index,
                "error": str(exc),
            }

        title = str(payload.get("title") or "")
        description = str(payload.get("description") or "")
        image_urls = [
            str(item).strip()
            for item in payload.get("imageUrls", [])
            if str(item).strip().startswith("http")
        ]
        images: list[dict] = []
        for image_index, image_url in enumerate(image_urls, start=1):
            images.append(
                {
                    "image_url": image_url,
                    "tag": self._guess_tag(title, description, source_page, image_index),
                    "source_page": source_page,
                    "note_title": title,
                    "note_description": description,
                    "note_index": note_index,
                    "image_index": image_index,
                }
            )
        return {
            "source_page": source_page,
            "note_title": title,
            "note_description": description,
            "images": images,
            "note_index": note_index,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def _extract_first_meta(self, html: str, names: list[str]) -> str:
        for name in names:
            patterns = [
                rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
                rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
                rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
                rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, html, flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return ""

    def _extract_title_tag(self, html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_image_urls(self, html: str) -> list[str]:
        candidates: list[str] = []
        patterns = [
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'"image"\s*:\s*"([^"]+)"',
            r'"imageList"\s*:\s*\[(.*?)\]',
        ]
        for pattern in patterns[:2]:
            candidates.extend(re.findall(pattern, html, flags=re.IGNORECASE))
        for match in re.findall(patterns[2], html, flags=re.IGNORECASE):
            if match.startswith("http"):
                candidates.append(match)
        image_list_matches = re.findall(patterns[3], html, flags=re.IGNORECASE | re.DOTALL)
        for block in image_list_matches:
            candidates.extend(re.findall(r'"url"\s*:\s*"([^"]+)"', block))
        normalized: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            url = item.replace("\\u002F", "/").replace("\\/", "/").strip()
            if not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            normalized.append(url)
        return normalized

    def _guess_tag(self, title: str, description: str, source_page: str, index: int) -> str:
        haystack = f"{title} {description} {source_page}".lower()
        for tag, keywords in self.tag_keywords.items():
            for keyword in keywords:
                if keyword.lower() in haystack:
                    return tag
        return self.default_tag_order[(index - 1) % len(self.default_tag_order)]

    def _infer_suffix(self, url: str) -> str:
        path = urlparse(url).path.lower()
        for suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            if path.endswith(suffix):
                return suffix
        return ".jpg"


class XiaohongshuMcpProvider:
    provider_name = "xiaohongshu-mcp"

    def collect(
        self,
        *,
        article_job_id: int,
        destination: str,
        article_context: dict,
        images_dir: Path,
        job_dir: Path,
        mcp_config: dict,
    ) -> list[GeneratedAsset]:
        preview = self.preview(
            destination=destination,
            article_context=article_context,
            limit=8,
            mcp_config=mcp_config,
        )
        assets: list[GeneratedAsset] = []
        with httpx.Client(timeout=30, follow_redirects=True, headers=self._headers()) as client:
            for index, image in enumerate(preview.get("images", [])[:10], start=1):
                image_url = str(image.get("image_url") or "")
                if not image_url:
                    continue
                response = client.get(image_url)
                response.raise_for_status()
                tag = str(image.get("tag") or "landmark")
                suffix = self._infer_suffix(str(response.url))
                image_path = images_dir / f"asset_{index:02d}_{tag}{suffix}"
                image_path.write_bytes(response.content)
                assets.append(
                    GeneratedAsset(
                        asset_type="image_source",
                        source_url=image_url,
                        local_path=image_path,
                        metadata={
                            "tag": tag,
                            "provider": self.provider_name,
                            "title": str(image.get("note_title") or ""),
                            "source_page": str(image.get("source_page") or ""),
                            "format": suffix.lstrip("."),
                            "kind": "xiaohongshu_mcp_image",
                            "caption_hint": f"{destination} {tag} 小红书 MCP 素材",
                            "note_index": image.get("note_index", 0),
                        },
                    )
                )
        return assets

    def preview(
        self,
        *,
        destination: str,
        article_context: dict,
        limit: int,
        mcp_config: dict,
    ) -> dict:
        client = XiaohongshuMcpClient(
            endpoint=str(mcp_config.get("endpoint") or ""),
            api_token=str(mcp_config.get("api_token") or ""),
            timeout_seconds=int(mcp_config.get("timeout_seconds") or 30),
            auth_header=str(mcp_config.get("auth_header") or "Authorization"),
        )
        keyword = (
            destination.strip()
            or str(article_context.get("title") or "").strip()
            or str(article_context.get("summary") or "").strip()
            or "旅行攻略"
        )
        search_result = client.search_notes(keyword, limit=limit)
        notes = self._extract_notes(search_result)
        flattened_images: list[dict] = []
        normalized_notes: list[dict] = []
        for note_index, note in enumerate(notes[:limit], start=1):
            detail_result = client.get_note_detail(note)
            payload = self._normalize_note_detail(note, detail_result, note_index)
            normalized_notes.append(payload)
            flattened_images.extend(payload["images"])
        return {
            "provider": self.provider_name,
            "discovery_mode": True,
            "seed_count": len(notes[:limit]),
            "note_count": len(normalized_notes),
            "image_count": len(flattened_images),
            "browser_diagnostics": {
                "enabled": True,
                "attempted": True,
                "blocked": False,
                "error_code": "",
                "error_message": "",
                "final_url": "",
            },
            "mcp_diagnostics": {
                "endpoint": str(mcp_config.get("endpoint") or ""),
                "enabled": bool(mcp_config.get("enabled")),
                "search_result_keys": list((search_result.get("structured") or {}).keys())
                if isinstance(search_result.get("structured"), dict)
                else [],
            },
            "notes": normalized_notes,
            "images": flattened_images,
        }

    def _extract_notes(self, search_result: dict) -> list[dict]:
        structured = search_result.get("structured")
        if isinstance(structured, dict):
            for key in ("notes", "items", "data", "list", "feeds"):
                value = structured.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
                if isinstance(value, dict):
                    for nested_key in ("items", "list", "notes", "feeds"):
                        nested = value.get(nested_key)
                        if isinstance(nested, list):
                            return [item for item in nested if isinstance(item, dict)]
        return []

    def _normalize_note_detail(self, source_note: dict, detail_result: dict, note_index: int) -> dict:
        structured = detail_result.get("structured")
        payload = structured if isinstance(structured, dict) else {}
        note_payload = payload.get("data", {}).get("note", {}) if isinstance(payload.get("data"), dict) else {}
        note_card = source_note.get("noteCard", {}) if isinstance(source_note.get("noteCard"), dict) else {}
        title = str(
            note_payload.get("title")
            or payload.get("title")
            or payload.get("note_title")
            or note_card.get("displayTitle")
            or source_note.get("title")
            or source_note.get("note_title")
            or ""
        )
        description = str(
            note_payload.get("desc")
            or payload.get("desc")
            or payload.get("description")
            or payload.get("note_description")
            or source_note.get("description")
            or ""
        )
        note_id = str(
            note_payload.get("noteId")
            or payload.get("feed_id")
            or source_note.get("id")
            or source_note.get("feed_id")
            or ""
        )
        xsec_token = str(
            note_payload.get("xsecToken")
            or payload.get("xsec_token")
            or source_note.get("xsecToken")
            or source_note.get("xsec_token")
            or ""
        )
        source_page = str(
            payload.get("url")
            or payload.get("link")
            or source_note.get("url")
            or source_note.get("link")
            or source_note.get("source_page")
            or (f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}" if note_id and xsec_token else "")
        )
        image_candidates = self._extract_image_candidates(note_payload or payload, note_card)
        images: list[dict] = []
        for image_index, image_url in enumerate(image_candidates, start=1):
            images.append(
                {
                    "image_url": image_url,
                    "tag": self._guess_tag(title, description, source_page, image_index),
                    "source_page": source_page,
                    "note_title": title,
                    "note_description": description,
                    "note_index": note_index,
                    "image_index": image_index,
                }
            )
        return {
            "source_page": source_page,
            "note_title": title,
            "note_description": description,
            "images": images,
            "note_index": note_index,
        }

    def _extract_image_candidates(self, payload: dict, note_card: dict | None = None) -> list[str]:
        candidates: list[str] = []

        def add_url(value: object) -> None:
            if isinstance(value, str) and value.startswith("http"):
                candidates.append(value)

        image_list = payload.get("imageList")
        if isinstance(image_list, list):
            for item in image_list:
                if isinstance(item, dict):
                    add_url(item.get("urlDefault") or item.get("urlPre") or item.get("url"))

        if note_card and isinstance(note_card, dict):
            cover = note_card.get("cover")
            if isinstance(cover, dict):
                add_url(cover.get("urlDefault") or cover.get("urlPre") or cover.get("url"))
            elif isinstance(cover, str):
                add_url(cover)

        def visit(value: object) -> None:
            if isinstance(value, str):
                if value.startswith("http") and any(
                    token in value.lower() for token in ("jpg", "jpeg", "png", "webp", "image", "xhscdn")
                ):
                    candidates.append(value)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    lowered = key.lower()
                    if lowered in {"image", "images", "url", "src", "cover", "covers", "image_list"} or lowered.startswith(
                        "url"
                    ) or "image" in lowered:
                        visit(item)
                    elif isinstance(item, (dict, list)):
                        visit(item)

        if not candidates:
            visit(payload)
            if note_card:
                visit(note_card)
        normalized: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            if item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized

    def _guess_tag(self, title: str, description: str, source_page: str, index: int) -> str:
        return XiaohongshuNoteScrapeProvider()._guess_tag(title, description, source_page, index)

    def _headers(self) -> dict[str, str]:
        return XiaohongshuNoteScrapeProvider()._headers()

    def _infer_suffix(self, url: str) -> str:
        return XiaohongshuNoteScrapeProvider()._infer_suffix(url)


class ImagePipelineService:
    providers: dict[str, ImageSourceProvider] = {
        MockXiaohongshuSvgProvider.provider_name: MockXiaohongshuSvgProvider(),
        DemoRemotePhotoProvider.provider_name: DemoRemotePhotoProvider(),
        ExternalUrlIngestProvider.provider_name: ExternalUrlIngestProvider(),
        XiaohongshuNoteScrapeProvider.provider_name: XiaohongshuNoteScrapeProvider(),
        XiaohongshuMcpProvider.provider_name: XiaohongshuMcpProvider(),
    }

    collage_palette = ["#d96c46", "#2d6a4f", "#355070", "#6d597a", "#bc6c25", "#1d3557"]

    def provider_status(self, provider_name: str | None = None) -> dict:
        current = provider_name or settings.image_source_provider
        return {
            "current_provider": current,
            "available_providers": list(self.providers.keys()),
            "uses_remote_download": current == DemoRemotePhotoProvider.provider_name,
            "uses_external_manifest": current == ExternalUrlIngestProvider.provider_name,
            "uses_xiaohongshu_seed_urls": current == XiaohongshuNoteScrapeProvider.provider_name,
            "uses_xiaohongshu_mcp": current == XiaohongshuMcpProvider.provider_name,
            "uses_browser_automation": current == XiaohongshuNoteScrapeProvider.provider_name,
            "playwright_available": sync_playwright is not None,
            "media_root": str(settings.media_path),
        }

    def collect_for_job(
        self,
        session: Session,
        article_job_id: int,
        official_account_id: int,
        destination: str,
        article_context: dict,
    ) -> dict:
        existing = session.exec(
            select(MediaAsset).where(MediaAsset.article_job_id == article_job_id)
        ).all()
        if existing:
            return self._summarize_assets(existing)

        job_dir = settings.media_path / "jobs" / str(article_job_id)
        images_dir = job_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        provider_name = app_settings_service.get_image_provider(session)
        provider = self.providers.get(
            provider_name,
            self.providers[MockXiaohongshuSvgProvider.provider_name],
        )
        xiaohongshu_mcp_config = app_settings_service.get_xiaohongshu_mcp_config(session)
        if provider_name == ExternalUrlIngestProvider.provider_name:
            generated = provider.collect(
                article_job_id=article_job_id,
                destination=destination,
                article_context=article_context,
                images_dir=images_dir,
                job_dir=job_dir,
                manifest=app_settings_service.get_external_image_manifest(session),
            )
        elif provider_name == XiaohongshuNoteScrapeProvider.provider_name:
            generated = provider.collect(
                article_job_id=article_job_id,
                destination=destination,
                article_context=article_context,
                images_dir=images_dir,
                job_dir=job_dir,
                seed_urls=app_settings_service.get_xiaohongshu_seed_urls(session),
            )
        elif provider_name == XiaohongshuMcpProvider.provider_name:
            generated = provider.collect(
                article_job_id=article_job_id,
                destination=destination,
                article_context=article_context,
                images_dir=images_dir,
                job_dir=job_dir,
                mcp_config=xiaohongshu_mcp_config,
            )
        else:
            generated = provider.collect(
                article_job_id=article_job_id,
                destination=destination,
                article_context=article_context,
                images_dir=images_dir,
                job_dir=job_dir,
            )

        created_assets: list[MediaAsset] = []
        for item in generated:
            asset = MediaAsset(
                article_job_id=article_job_id,
                official_account_id=official_account_id,
                asset_type=item.asset_type,
                source_url=item.source_url,
                local_path=str(item.local_path),
                upload_role="content",
                metadata_json=json.dumps(item.metadata, ensure_ascii=False),
            )
            session.add(asset)
            created_assets.append(asset)

        collage_path = job_dir / "cover_collage.svg"
        collage_path.write_text(
            self._render_collage_svg(destination=destination, assets=generated[:6]),
            encoding="utf-8",
        )
        collage_asset = MediaAsset(
            article_job_id=article_job_id,
            official_account_id=official_account_id,
            asset_type="cover_collage",
            source_url="",
            local_path=str(collage_path),
            upload_role="thumb",
            metadata_json=json.dumps(
                {
                    "layout": "magazine-freeform",
                    "source_count": min(6, len(generated)),
                    "format": "svg",
                        "provider": provider.provider_name,
                },
                ensure_ascii=False,
            ),
        )
        session.add(collage_asset)
        created_assets.append(collage_asset)
        session.commit()
        return self._summarize_assets(created_assets)

    def preview_xiaohongshu_seed_urls(
        self,
        seed_urls: list[str],
        *,
        destination: str = "",
        article_context: dict | None = None,
        limit: int = 8,
    ) -> dict:
        provider = self.providers[XiaohongshuNoteScrapeProvider.provider_name]
        return provider.preview(
            seed_urls,
            destination=destination,
            article_context=article_context or {},
            limit=limit,
        )

    def preview_xiaohongshu_mcp(
        self,
        *,
        destination: str = "",
        article_context: dict | None = None,
        limit: int = 8,
        mcp_config: dict | None = None,
    ) -> dict:
        provider = self.providers[XiaohongshuMcpProvider.provider_name]
        return provider.preview(
            destination=destination,
            article_context=article_context or {},
            limit=limit,
            mcp_config=mcp_config or {},
        )

    def rebuild_for_job(
        self,
        session: Session,
        article_job_id: int,
        official_account_id: int,
        destination: str,
        article_context: dict,
    ) -> dict:
        assets = session.exec(
            select(MediaAsset).where(MediaAsset.article_job_id == article_job_id)
        ).all()
        for asset in assets:
            if asset.local_path:
                path = Path(asset.local_path)
                if path.exists():
                    path.unlink(missing_ok=True)
            session.delete(asset)
        session.commit()

        job_dir = settings.media_path / "jobs" / str(article_job_id)
        images_dir = job_dir / "images"
        if images_dir.exists():
            for item in images_dir.iterdir():
                if item.is_file():
                    item.unlink(missing_ok=True)
        collage = job_dir / "cover_collage.svg"
        if collage.exists():
            collage.unlink(missing_ok=True)

        return self.collect_for_job(
            session=session,
            article_job_id=article_job_id,
            official_account_id=official_account_id,
            destination=destination,
            article_context=article_context,
        )

    def _render_collage_svg(self, destination: str, assets: list[GeneratedAsset]) -> str:
        cards = []
        placements = [
            (70, 90, 320, 220),
            (420, 70, 300, 200),
            (770, 110, 340, 240),
            (120, 380, 280, 200),
            (460, 330, 310, 230),
            (820, 430, 250, 180),
        ]
        for index, (asset, (x, y, w, h)) in enumerate(zip(assets, placements), start=1):
            color = self.collage_palette[(index - 1) % len(self.collage_palette)]
            label = escape(asset.metadata.get("tag", "image").replace("_", " ").title())
            source_kind = escape(asset.metadata.get("kind", "asset"))
            cards.append(
                f"""
  <g transform="translate({x},{y}) rotate({(x + y) % 7 - 3})">
    <rect width="{w}" height="{h}" rx="28" fill="white" opacity="0.96"/>
    <rect x="14" y="14" width="{w - 28}" height="{h - 28}" rx="22" fill="{color}" opacity="0.18"/>
    <text x="28" y="52" fill="{color}" font-size="24" font-family="Georgia, serif">{label}</text>
    <text x="28" y="{h - 58}" fill="#333" font-size="18" font-family="Georgia, serif">#{index:02d}</text>
    <text x="28" y="{h - 28}" fill="#555" font-size="14" font-family="Georgia, serif">{source_kind}</text>
  </g>
"""
            )
        safe_destination = escape(destination)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="900" viewBox="0 0 1200 900">
  <rect width="1200" height="900" fill="#f5efe6"/>
  <text x="70" y="58" fill="#1d5c4f" font-size="24" font-family="Georgia, serif" letter-spacing="4">MAGAZINE COLLAGE</text>
  <text x="70" y="860" fill="#1e1b18" font-size="56" font-family="Georgia, serif">{safe_destination}</text>
  {''.join(cards)}
</svg>
"""

    def _summarize_assets(self, assets: list[MediaAsset]) -> dict:
        image_assets = [asset for asset in assets if asset.asset_type == "image_source"]
        collage = next((asset for asset in assets if asset.asset_type == "cover_collage"), None)
        return {
            "provider": (
                json.loads(collage.metadata_json or "{}").get("provider")
                if collage
                else settings.image_source_provider
            ),
            "image_count": len(image_assets),
            "images": [
                {
                    "id": asset.id,
                    "local_path": asset.local_path,
                    "source_url": asset.source_url,
                    "metadata": json.loads(asset.metadata_json or "{}"),
                }
                for asset in image_assets
            ],
            "collage": {
                "id": collage.id if collage else None,
                "local_path": collage.local_path if collage else "",
                "metadata": json.loads(collage.metadata_json or "{}") if collage else {},
            },
        }


image_pipeline_service = ImagePipelineService()
