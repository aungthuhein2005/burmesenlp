"""Download external corpus resources into the local cache."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .cache import cache_dir
from .registry import resource_info


class DownloadError(RuntimeError):
    """Raised when a corpus download fails."""


def download(
    name_or_url: str,
    *,
    filename: Optional[str] = None,
    force: bool = False,
) -> Path:
    """Download a registered or arbitrary URL into the corpus cache.

    * If *name_or_url* is a registry name with a ``url`` field (from
      ``metadata/corpus.json``), that URL is fetched.
    * If it looks like an ``http(s)`` URL, it is fetched directly.
    * Returns the path of the cached file.
    """
    url: Optional[str] = None
    dest_name = filename

    info = resource_info(name_or_url)
    if info is not None:
        url = info.get("url")
        if dest_name is None:
            dest_name = Path(info.get("path", name_or_url)).name
        if not url:
            raise DownloadError(
                f"resource {name_or_url!r} is bundled locally and has no download URL"
            )
    elif name_or_url.startswith(("http://", "https://")):
        url = name_or_url
        if dest_name is None:
            dest_name = Path(urlparse(url).path).name or "download.bin"
    else:
        raise DownloadError(
            f"unknown resource {name_or_url!r}; pass a registry name with a "
            f"url, or an http(s) URL"
        )

    assert url is not None and dest_name is not None
    dest = cache_dir() / dest_name
    if dest.is_file() and not force:
        return dest

    tmp = dest.with_suffix(dest.suffix + ".partial")
    try:
        urllib.request.urlretrieve(url, tmp)  # noqa: S310 - user-supplied corpus URL
        tmp.replace(dest)
    except (urllib.error.URLError, OSError) as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise DownloadError(f"failed to download {url!r}: {exc}") from exc
    return dest
