#!/usr/bin/env python3
"""Yetkinlik OS: collect public RSS/Atom feeds; fall back to Google News RSS search.

No API keys, no paid extraction, no fabricated summaries or translations.
Run with: python scripts/fetch_news.py
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "sources.json"
DEST = ROOT / "site" / "data" / "news.json"
HEADERS = {"User-Agent": "YetkinlikOS-RSS/1.0 (personal feed reader; public RSS/Atom only)", "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml,text/html;q=0.8,*/*;q=0.2"}
MAX_BYTES = 1_500_000
DAYS_TO_KEEP = 45
MAX_RECORDS = 260
MAX_PER_SOURCE = 8

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

class Stripper(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in ("script", "style", "noscript"): self.skip += 1
        if tag.lower() in ("p", "br", "li"): self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style", "noscript") and self.skip: self.skip -= 1
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)

def plain(value: str, limit=500) -> str:
    h = Stripper()
    try: h.feed(str(value or ""))
    except Exception: return ""
    return re.sub(r"\s+", " ", html.unescape(" ".join(h.parts))).strip()[:limit]

def get(url: str) -> tuple[bytes, str]:
    if not url.lower().startswith("https://"): raise ValueError("Only HTTPS feeds supported")
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES: raise ValueError("Page/feed too large")
        return content, response.url

def direct_child(node: ET.Element, names: tuple[str, ...]) -> str:
    for ch in node:
        name = ch.tag.split("}")[-1].lower()
        if name in names and ch.text and ch.text.strip(): return ch.text.strip()
    return ""

def dated(value: str, now: datetime) -> datetime | None:
    if not value: return None
    try:
        d = parsedate_to_datetime(value)
    except Exception:
        try: d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception: return None
    if not d.tzinfo: d = d.replace(tzinfo=timezone.utc)
    d = d.astimezone(timezone.utc)
    if d > now + timedelta(days=1): return None
    return d

def canonical(url: str) -> str:
    try:
        o = urllib.parse.urlsplit(url.strip())
        if o.scheme not in ("http", "https"): return ""
        q = [(k, v) for k, v in urllib.parse.parse_qsl(o.query) if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")]
        return urllib.parse.urlunsplit((o.scheme, o.netloc.lower(), o.path.rstrip("/") or "/", urllib.parse.urlencode(q), ""))
    except Exception: return ""

def parse_xml(content: bytes, source: dict, provider: str, now: datetime) -> list[dict[str, Any]]:
    tree = ET.fromstring(content)
    root = tree.tag.split("}")[-1].lower()
    if root in ("rss", "rdf"):
        entries = [node for node in tree.iter() if node.tag.split("}")[-1].lower() == "item"]
        is_atom = False
    elif root == "feed":
        entries = [node for node in tree if node.tag.split("}")[-1].lower() == "entry"]
        is_atom = True
    else:
        raise ValueError("Not RSS/Atom XML")
    records = []
    for ent in entries[:55]:
        title = plain(direct_child(ent, ("title",)), 250)
        url = direct_child(ent, ("link", "origlink"))
        if is_atom:
            url = next((c.attrib.get("href", "") for c in ent if c.tag.split("}")[-1].lower() == "link" and c.attrib.get("rel", "alternate") in ("alternate", "")), url)
        date = dated(direct_child(ent, ("pubdate", "published", "updated", "date")), now)
        raw_summary = direct_child(ent, ("description", "summary", "encoded", "content"))
        if date is None or date < now - timedelta(days=DAYS_TO_KEEP) or not title: continue
        url = canonical(url)
        if not url: continue
        if provider == "Google News RSS":
            # Google News may append its source to the title; keep titles unchanged for transparency.
            raw_summary = "Bu başlık Google News RSS aramasından alınmıştır. Yayıncının tam içeriği için bağlantıyı aç."
        body = plain(raw_summary, 480)
        id_key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        records.append({"id": "auto-" + id_key, "sourceId": source["id"], "title": title,
            "date": date.date().isoformat(), "publishedAt": date.isoformat(timespec="seconds"),
            "url": url, "summary": body, "action": "Makaleyi aç; öğrenebileceğin bir fikri not et.",
            "priority": "Okuma listesi", "provider": provider})
    return records

class FeedLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.feeds = []
    def handle_starttag(self, tag, attrs):
        if tag != "link": return
        data = dict(attrs)
        typ = (data.get("type") or "").lower()
        if typ in ("application/rss+xml", "application/atom+xml") and data.get("href"): self.feeds.append(data["href"])

def discovered_feed(page: str) -> str:
    content, resolved = get(page)
    h = FeedLinks()
    h.feed(content.decode("utf-8", errors="replace")[:MAX_BYTES])
    if not h.feeds: return ""
    return urllib.parse.urljoin(resolved, h.feeds[0])

def google_feed(source: dict) -> str:
    q = source.get("query", "").strip()
    if not q:
        site = urllib.parse.urlsplit(source.get("url", "")).hostname
        if not site: return ""
        q = "site:" + site.removeprefix("www.")
    q += " when:30d"
    params = urllib.parse.urlencode({"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    return "https://news.google.com/rss/search?" + params

def collect_source(source: dict, now: datetime) -> tuple[list[dict], dict]:
    status = {"id": source["id"], "name": source["name"], "count": 0, "status": "unavailable", "provider": "", "message": ""}
    if source.get("mode") == "archive":
        status.update(status="archive", message="Tarihsel kaynak: yeni yayın taraması yapılmıyor")
        return [], status
    candidates: list[tuple[str, str]] = []
    if source.get("feed"): candidates.append((source["feed"], "Resmi RSS/Atom (yapılandırılmış)"))
    if source.get("url") and source.get("type") not in ("Konu", "Eğitim"):
        try:
            found = discovered_feed(source["url"])
            if found and found not in [c[0] for c in candidates]: candidates.append((found, "Siteden keşfedilen RSS/Atom"))
        except Exception as exc:
            logging.info("%s feed discovery: %s", source['id'], str(exc)[:90])
    fallback = google_feed(source)
    if fallback: candidates.append((fallback, "Google News RSS"))
    errors = []
    for url, provider in candidates:
        try:
            content, _ = get(url)
            items = parse_xml(content, source, provider, now)
            if not items:
                errors.append(provider + ": yakın tarihli içerik yok")
                continue
            items.sort(key=lambda x: x["publishedAt"], reverse=True)
            status.update(count=min(len(items),MAX_PER_SOURCE), status="ok", provider=provider, message="")
            return items[:MAX_PER_SOURCE], status
        except Exception as exc:
            errors.append(provider + ": " + str(exc)[:95])
    status["message"] = "; ".join(errors)[:240] or "Uygun otomatik yayın adresi bulunamadı"
    return [], status

def main() -> None:
    now = datetime.now(timezone.utc)
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    sources = data["sources"]
    existing = {}
    previous = {}
    if DEST.exists():
        try:
            previous = json.loads(DEST.read_text(encoding="utf-8"))
            for a in previous.get("articles", []):
                if a.get("id", "").startswith("auto-") and a.get("date", "") >= (now-timedelta(days=DAYS_TO_KEEP)).date().isoformat():
                    existing[a["id"]] = a
        except Exception as exc: logging.warning("Could not read prior archive: %s", exc)
    statuses = []
    failures = 0
    for i, source in enumerate(sources, 1):
        logging.info("(%d/%d) %s", i, len(sources), source["name"])
        try: items, status = collect_source(source, now)
        except Exception as exc:
            items, status = [], {"id": source["id"], "name": source["name"], "status": "unavailable", "count":0,"provider":"","message":str(exc)[:200]}
        for a in items: existing[a["id"]] = a
        statuses.append(status)
        failures += status["status"] == "unavailable"
    stored = list(existing.values())
    stored.sort(key=lambda a: (a.get("publishedAt",a["date"]), a["id"]), reverse=True)
    stored = stored[:MAX_RECORDS]
    payload = {"schemaVersion": 1, "generatedAt": now.isoformat(timespec="seconds"),
        "timezone": "Europe/Istanbul", "retentionDays": DAYS_TO_KEEP,
        "articles": stored, "sources": statuses, "sourceCount": len(sources),
        "successCount": sum(s["status"]=="ok" for s in statuses),
        "unavailableCount": failures,
        "disclaimer": "Otomatik RSS başlıkları ve yayıncı özetleri. AI özeti varsa yalnızca mevcut açıklamalara dayanır. Google News RSS tüm içerikleri kapsamayabilir."}
    # The collector must not erase the last generated digest before the next
    # step runs. Keeping it allows same-day AI results to be reused without
    # spending again on unchanged input, and keeps the user's 14-day archive.
    if isinstance(previous.get("dailyDigest"), dict):
        payload["dailyDigest"] = previous["dailyDigest"]
    if isinstance(previous.get("digestHistory"), list):
        payload["digestHistory"] = previous["digestHistory"][:14]
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logging.info("Written %d stories from %d active sources; %d unavailable",len(stored),payload['successCount'],failures)
    # Don't destroy prior data in case of temporary network outage; pipeline completes and surfaces statuses.

if __name__ == "__main__": main()