# Copyright Thinking Cars GmbH
# SPDX-License-Identifier: LicenseRef-NvidiaSourceCodeLicense-NC

"""Lazy download of the FocalFormer3D model checkpoint.

The checkpoint (~189 MiB) is not part of this repository. It is fetched from the download
location published by the original authors on first use of the node and cached on disk,
s.t. subsequent starts reuse the local copy.

Only the standard library is used: the Google Drive download requires following a
"virus scan warning" interstitial, which is a single extra request (see `_google_drive_url`).
"""

import hashlib
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Callable, Optional

# checkpoint published by NVlabs (FocalFormer3D_L, nuScenes, mAP 66.4 / NDS 70.9),
# linked from the original repository README
CHECKPOINT_URL = "https://drive.google.com/file/d/1OMj00n_pbAotlGi2JyqptYSgpt6mfyu5/view?usp=sharing"
CHECKPOINT_SHA256 = "decbe8751a568dd5d308c7e2ae430c2c7ca761c8948f3974e30a68876887335c"

_DRIVE_DOWNLOAD_ENDPOINT = "https://drive.usercontent.google.com/download"
# Drive rejects requests without a browser-like user agent
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
_CHUNK_SIZE = 1 << 20  # 1 MiB


class _FormParser(HTMLParser):
    """Extracts the action and the hidden inputs of the Google Drive confirmation form."""

    def __init__(self):
        super().__init__()
        self.action: Optional[str] = None
        self.fields: dict[str, str] = {}
        self._in_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        attributes = dict(attrs)
        if tag == "form":
            self._in_form = True
            self.action = attributes.get("action")
        elif tag == "input" and self._in_form:
            name, value = attributes.get("name"), attributes.get("value")
            if name and value is not None:
                self.fields[name] = value

    def handle_endtag(self, tag: str):
        if tag == "form":
            self._in_form = False


def _google_drive_file_id(url: str) -> Optional[str]:
    """Extracts the file ID from a Google Drive share URL.

    Args:
        url (str): URL to inspect, e.g. `https://drive.google.com/file/d/<ID>/view?usp=sharing`

    Returns:
        Optional[str]: file ID, or None if `url` is not a Google Drive URL
    """

    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc.endswith("google.com"):
        return None

    match = re.search(r"/file/d/([^/]+)", parsed.path)
    if match:
        return match.group(1)
    return urllib.parse.parse_qs(parsed.query).get("id", [None])[0]


def _open(url: str, opener: urllib.request.OpenerDirector):
    """Opens a URL with a browser-like user agent."""

    return opener.open(urllib.request.Request(url, headers={"User-Agent": _USER_AGENT}), timeout=60)


def _google_drive_url(file_id: str, opener: urllib.request.OpenerDirector) -> str:
    """Resolves the direct download URL for a Google Drive file.

    Files above the virus-scan size limit are served behind a confirmation page; its form has to
    be submitted (carrying a per-request `uuid`) to obtain the file itself.

    Args:
        file_id (str): Google Drive file ID
        opener (urllib.request.OpenerDirector): opener holding the session cookies

    Returns:
        str: URL serving the file content

    Raises:
        RuntimeError: if Drive keeps returning HTML, e.g. because the download quota is exceeded
    """

    query = urllib.parse.urlencode({"id": file_id, "export": "download"})
    url = f"{_DRIVE_DOWNLOAD_ENDPOINT}?{query}"

    with _open(url, opener) as response:
        if "text/html" not in response.headers.get("Content-Type", ""):
            return url  # small file, served directly
        page = response.read().decode("utf-8", errors="replace")

    parser = _FormParser()
    parser.feed(page)
    if not parser.action or not parser.fields:
        message = re.sub(r"<[^>]+>", " ", page)
        raise RuntimeError(
            f"Google Drive did not serve the file for ID '{file_id}'. This usually means the "
            f"download quota is exceeded or the file is no longer shared. Response: {' '.join(message.split())[:300]}"
        )

    return f"{parser.action}?{urllib.parse.urlencode(parser.fields)}"


def _download(url: str, destination: str, log: Callable[[str], None]):
    """Downloads a URL to a local file, reporting progress.

    The download goes to a temporary file in the target directory that is moved into place only
    after completion, s.t. an interrupted download is never mistaken for a cached checkpoint.

    Args:
        url (str): checkpoint URL, may be a Google Drive share URL
        destination (str): path to write the file to
        log (Callable[[str], None]): callback for progress messages

    Raises:
        RuntimeError: if the server responds with HTML instead of the file content
    """

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    file_id = _google_drive_file_id(url)
    if file_id is not None:
        url = _google_drive_url(file_id, opener)

    directory = os.path.dirname(destination)
    with _open(url, opener) as response:
        if "text/html" in response.headers.get("Content-Type", ""):
            raise RuntimeError(f"Expected file content but received an HTML page from '{url}'")
        total_bytes = int(response.headers.get("Content-Length", 0))

        # NamedTemporaryFile in the target directory keeps the final move atomic (same filesystem)
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".download-", delete=False) as temporary_file:
            temporary_path = temporary_file.name
            try:
                downloaded_bytes, next_report = 0, 0
                while chunk := response.read(_CHUNK_SIZE):
                    temporary_file.write(chunk)
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes >= next_report:
                        progress = f" ({100 * downloaded_bytes / total_bytes:.0f}%)" if total_bytes else ""
                        log(f"Downloaded {downloaded_bytes / 2**20:.0f}MiB{progress} ...")
                        next_report = downloaded_bytes + 32 * 2**20
            except BaseException:
                os.unlink(temporary_path)
                raise

    shutil.move(temporary_path, destination)
    os.chmod(destination, 0o644)


def _sha256(path: str) -> str:
    """Computes the SHA-256 checksum of a file."""

    digest = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_checkpoint(
    destination: str,
    url: str = CHECKPOINT_URL,
    expected_sha256: Optional[str] = CHECKPOINT_SHA256,
    log: Callable[[str], None] = print,
) -> str:
    """Returns a local path to the model checkpoint, downloading it if it is not cached yet.

    Args:
        destination (str): path the checkpoint is cached at
        url (str, optional): URL to download the checkpoint from
        expected_sha256 (Optional[str], optional): expected checksum, or None to skip verification
        log (Callable[[str], None], optional): callback for progress messages

    Returns:
        str: path to the verified checkpoint file (equal to `destination`)

    Raises:
        RuntimeError: if the download fails or the downloaded file does not match `expected_sha256`
    """

    if os.path.isfile(destination):
        if expected_sha256 is None or _sha256(destination) == expected_sha256:
            log(f"Using cached model checkpoint '{destination}'")
            return destination
        log(f"Cached model checkpoint '{destination}' is corrupted (checksum mismatch), downloading it again")

    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    log(f"Downloading model checkpoint from '{url}' to '{destination}' (~189MiB, first use only) ...")
    _download(url, destination, log)

    if expected_sha256 is not None:
        checksum = _sha256(destination)
        if checksum != expected_sha256:
            os.unlink(destination)
            raise RuntimeError(
                f"Checksum of the downloaded model checkpoint does not match: "
                f"expected '{expected_sha256}', got '{checksum}'"
            )

    log(f"Downloaded model checkpoint to '{destination}'")

    return destination
