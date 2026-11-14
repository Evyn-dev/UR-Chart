"""Optional NIH MedlinePlus education lookup for *fictional* UR Chart questions.

Only fixed, non-identifying topic strings leave the server; never send questions,
patient records, medications, access tokens, or recovery history to the service.
This is reference retrieval, not clinical evidence grading or medical advice.
"""
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from threading import Lock
from time import monotonic
from urllib.parse import urlparse
import re
import xml.etree.ElementTree as ET

import httpx

ENDPOINT = "https://wsearch.nlm.nih.gov/ws/query"
TTL_SECONDS = 24 * 60 * 60
MAX_REFERENCES = 2
# The most specific topic match wins. Query strings are fixed, not user-supplied.
TOPICS = (
    (r"\b(cabg|coronary bypass|bypass surgery)\b", "coronary artery bypass"),
    (r"\b(heart valve|valve replacement|valve surgery)\b", "heart valve diseases"),
    (r"\b(hip replacement|hip arthroplasty)\b", "hip replacement"),
    (r"\b(knee replacement|knee arthroplasty)\b", "knee replacement"),
    (r"\b(abdominal surgery|abdominal operation)\b", "after surgery"),
    (r"\b(cardiac rehab|cardiac rehabilitation)\b", "cardiac rehabilitation"),
    (r"\b(incision|wound care|wound healing|stitches)\b", "surgical wound care"),
    (r"\b(medication|medicine|prescription|drug|side effect|refill)\b", "medication safety"),
    (r"\b(breathing problems|breathlessness|shortness of breath)\b", "breathing problems"),
    (r"\b(chest pain|chest pressure)\b", "chest pain"),
    (r"\b(fever|infection)\b", "infections"),
    (r"\b(pain management|pain relief)\b", "pain"),
)
_cache: dict[str, tuple[float, tuple["MedicalReference", ...]]] = {}
_cache_lock = Lock()


@dataclass(frozen=True)
class MedicalReference:
    title: str
    url: str
    excerpt: str


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, text: str):
        self.parts.append(text)


def _plain(value: str) -> str:
    reader = _TextOnly()
    reader.feed(value)
    return re.sub(r"\s+", " ", unescape(" ".join(reader.parts))).strip()


def _topics_from_message(message: str) -> list[str]:
    # Match only the user's submitted message. Never send the message itself.
    found = [topic for pattern, topic in TOPICS if re.search(pattern, message, re.I)]
    return list(dict.fromkeys(found))[:MAX_REFERENCES]


def _parse(xml_text: str) -> tuple[MedicalReference, ...]:
    # ET does not resolve remote XML entities. Cap response size in _lookup.
    root = ET.fromstring(xml_text)
    results = []
    for document in root.findall("./list/document")[:3]:
        url = document.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"medlineplus.gov", "www.medlineplus.gov"}:
            continue
        contents = {part.get("name", "").lower(): "".join(part.itertext())
                    for part in document.findall("content")}
        title = _plain(contents.get("title", ""))[:140]
        excerpt = _plain(contents.get("fullsummary", "") or contents.get("snippet", ""))[:850]
        if title and excerpt:
            results.append(MedicalReference(title, url, excerpt))
    return tuple(results[:2])


def _lookup(topic: str) -> tuple[MedicalReference, ...]:
    now = monotonic()
    with _cache_lock:
        cached = _cache.get(topic)
        if cached and now - cached[0] < TTL_SECONDS:
            return cached[1]
    try:
        response = httpx.get(
            ENDPOINT,
            params={"db": "healthTopics", "term": topic, "retmax": 2,
                    "rettype": "brief", "tool": "URChartHackathon"},
            timeout=3.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        if len(response.content) > 250_000:
            return ()
        found = _parse(response.text)
    except (httpx.HTTPError, ET.ParseError, ValueError, UnicodeError):
        return ()
    with _cache_lock:
        # Bound memory if the topic catalog is ever expanded.
        if len(_cache) > 64:
            _cache.clear()
        _cache[topic] = (monotonic(), found)
    return found


def find_references(message: str) -> tuple[MedicalReference, ...]:
    """Retrieve at most two MedlinePlus topics; never transmit patient data."""
    topics = _topics_from_message(message)
    return tuple(ref for topic in topics for ref in _lookup(topic))[:MAX_REFERENCES]


def references_as_text(references: tuple[MedicalReference, ...]) -> str:
    if not references:
        return ""
    return "\n".join(
        f"[{i}] {item.title} (MedlinePlus, US National Library of Medicine)\n"
        f"URL: {item.url}\nReference excerpt: {item.excerpt}"
        for i, item in enumerate(references, 1)
    )


def reference_links(references: tuple[MedicalReference, ...]) -> str:
    if not references:
        return ""
    return "\n\nEducational references (NIH MedlinePlus, not personal medical advice):\n" + "\n".join(
        f"- {item.title}: {item.url}" for item in references
    )
