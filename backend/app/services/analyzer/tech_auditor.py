"""
Tech audit — basic fingerprinting of website tech stack (T5).

Uses the WebsiteAudit result + a couple of cheap GETs to detect:
  - CMS (WordPress, Wix, Squarespace) by meta generator tag
  - CDN (Cloudflare, Cloudfront) by headers
  - Framework (Next.js, React) by response patterns

For v1 we only do header-level fingerprinting (no full HTML parse).
The hook_generator (LLM) can do deeper analysis if available.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.analyzer.website_checker import WebsiteAudit

logger = logging.getLogger("clientfinder.analyzer.tech")


# Common CMS signatures
CMS_SIGNATURES: dict[str, list[str]] = {
    "wordpress": ["wp-content", "wp-includes", "wordpress"],
    "wix": ["wix.com", "wixsite"],
    "squarespace": ["squarespace"],
    "shopify": ["cdn.shopify", "shopify.com"],
    "joomla": ["/joomla/", "Joomla!"],
    "drupal": ["Drupal", "drupal.org"],
    "ghost": ["ghost.io", "ghost-app"],
    "webflow": ["webflow"],
}

# CDN signatures (from headers)
CDN_SIGNATURES: dict[str, list[str]] = {
    "cloudflare": ["cloudflare", "cf-ray"],
    "cloudfront": ["cloudfront", "x-amz-cf-id"],
    "fastly": ["fastly", "x-served-by"],
    "akamai": ["akamai"],
    "vercel": ["x-vercel-id", "vercel"],
    "netlify": ["x-nf-request-id", "netlify"],
}

# Framework signatures (basic)
FRAMEWORK_SIGNATURES: dict[str, list[str]] = {
    "next.js": ["x-nextjs", "next/static", "_next"],
    "react": ["react"],
    "vue": ["vue", "_nuxt"],
    "laravel": ["laravel", "csrf-token"],
}


@dataclass
class TechAudit:
    cms: str | None = None
    cdn: str | None = None
    framework: str | None = None
    server: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def audit_tech(site: WebsiteAudit, html_snippet: str | None = None) -> TechAudit:
    """
    Fingerprint the tech stack from a WebsiteAudit.

    `html_snippet` is optional — pass a snippet of HTML if you have
    one for deeper fingerprinting. For v1 we just use headers.
    """
    result = TechAudit(server=site.server)

    # Server header
    if site.server:
        result.server = site.server[:200]

    # CDN detection (from header keys)
    headers_lower = {k.lower() for k in site.extra.get("headers_seen", [])}
    for cdn, sigs in CDN_SIGNATURES.items():
        if any(s in h for h in headers_lower for s in sigs):
            result.cdn = cdn
            break

    # HTML-level signatures (if provided)
    haystack_parts = []
    if site.powered_by:
        haystack_parts.append(site.powered_by)
    if html_snippet:
        haystack_parts.append(html_snippet.lower()[:50_000])
    haystack = " ".join(haystack_parts).lower()

    if haystack:
        for cms, sigs in CMS_SIGNATURES.items():
            if any(s.lower() in haystack for s in sigs):
                result.cms = cms
                break
        if not result.cms:
            for fw, sigs in FRAMEWORK_SIGNATURES.items():
                if any(s.lower() in haystack for s in sigs):
                    result.framework = fw
                    break

    return result
