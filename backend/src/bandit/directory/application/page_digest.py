"""Reduce el HTML a texto y enlaces para gastar menos tokens y aislar el contenido."""

from dataclasses import dataclass
from urllib.parse import urljoin

from selectolax.lexbor import LexborHTMLParser, LexborNode

_NOISE = ("script", "style", "noscript", "svg", "header", "footer", "nav", "form")


@dataclass(frozen=True, slots=True)
class PageDigest:
    text: str
    urls: frozenset[str]


def digest_html(html: str, base_url: str) -> PageDigest:
    tree = LexborHTMLParser(html)
    tree.strip_tags(list(_NOISE))
    root: LexborNode | None = tree.css_first("main") or tree.body
    if root is None:
        return PageDigest("", frozenset())

    urls: set[str] = set()
    for element in root.css("img, a"):
        attribute = "src" if element.tag == "img" else "href"
        value = element.attributes.get(attribute)
        if not value or value.startswith(("mailto:", "tel:", "data:", "#")):
            continue
        absolute = urljoin(base_url, value)
        urls.add(absolute)
        element.insert_after(f" [{element.tag}: {absolute}] ")

    return PageDigest(root.text(separator=" ", strip=True), frozenset(urls))
