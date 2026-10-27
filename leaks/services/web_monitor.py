import hashlib
import ipaddress
import json
import socket
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup
from django.conf import settings

from leaks.models import Source

from .ingestion import create_upload


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute HTTP/HTTPS public URLs are allowed.")
    for item in socket.getaddrinfo(
        parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
    ):
        ip = ipaddress.ip_address(item[4][0])
        if not ip.is_global:
            raise ValueError(
                "Private, loopback, reserved and link-local network targets are blocked."
            )


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        parser.read()
        return parser.can_fetch(settings.MONITOR_USER_AGENT, url)
    except OSError:
        return False


def fetch_public_content(url: str) -> tuple[bytes, str, str]:
    validate_public_url(url)
    if not _robots_allowed(url):
        raise PermissionError("Source robots policy does not authorize this fetch.")
    response = requests.get(
        url,
        headers={"User-Agent": settings.MONITOR_USER_AGENT},
        timeout=(5, 20),
        allow_redirects=False,
        stream=True,
    )
    response.raise_for_status()
    if 300 <= response.status_code < 400:
        raise ValueError("Redirects are disabled; configure the final public URL.")
    chunks, size = [], 0
    for chunk in response.iter_content(65536):
        size += len(chunk)
        if size > settings.MONITOR_MAX_BYTES:
            raise ValueError("Response exceeds configured evidence size limit.")
        chunks.append(chunk)
    data = b"".join(chunks)
    content_type = response.headers.get("Content-Type", "").split(";")[0].lower()
    return data, content_type, response.url


def monitor_web_source(source: Source) -> int:
    if source.access_scope != Source.Scope.PUBLIC:
        raise PermissionError("Web monitoring is limited to public sources.")
    data, content_type, final_url = fetch_public_content(source.endpoint)
    if (
        content_type == "application/json"
        and source.source_type == Source.Type.SEARCH_FEED
    ):
        payload = json.loads(data)
        items = (
            payload.get("items")
            or payload.get("results")
            or (payload.get("webPages") or {}).get("value")
            or []
        )
        count = 0
        for item in items[: int(source.config.get("max_items", 25))]:
            url = item.get("link") or item.get("url") or ""
            title = item.get("title") or item.get("name") or ""
            summary = (
                item.get("snippet") or item.get("description") or item.get("text") or ""
            )
            external_id = str(item.get("id") or url or f"result-{count}")
            create_upload(
                source=source,
                external_id=external_id,
                text=f"{title}\n{summary}",
                original_url=url,
                content_type="text/plain",
                metadata={"provider_result": True},
            )
            count += 1
        return count
    if (
        content_type
        in {
            "application/rss+xml",
            "application/atom+xml",
            "text/xml",
            "application/xml",
        }
        or source.source_type == Source.Type.RSS
    ):
        feed = feedparser.parse(data)
        count = 0
        for entry in feed.entries[: int(source.config.get("max_items", 25))]:
            url = entry.get("link", "")
            text = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(
                " ", strip=True
            )
            create_upload(
                source=source,
                external_id=entry.get("id", url),
                text=f"{entry.get('title', '')}\n{text}",
                original_url=url,
                content_type="text/plain",
            )
            count += 1
        return count
    if content_type.startswith("text/html"):
        soup = BeautifulSoup(data, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        create_upload(
            source=source,
            external_id=f"snapshot:{digest}",
            text=text,
            original_url=final_url,
            content_type=content_type,
        )
    else:
        filename = Path(urlparse(final_url).path).name or "web-evidence.bin"
        create_upload(
            source=source,
            external_id=f"sha256:{hashlib.sha256(data).hexdigest()}",
            content=data,
            filename=filename,
            original_url=final_url,
            content_type=content_type,
        )
    return 1
