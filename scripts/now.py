"""
Puts what paolo.sh says I'm listening to and watching into the README,
between the <!--music--> and <!--movie--> markers. If the site can't be
reached, the README is left as it is.

usage: python3 scripts/now.py README.md
"""

import json
import re
import sys
import urllib.request

SITE = "https://www.paolo.sh"


def fetch(path):
    request = urllib.request.Request(SITE + path, headers={"User-Agent": "profile-readme-updater"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def md(title):
    """A title as Markdown text: its own *, _, [ and ] can't start formatting."""
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", title.strip())


def put(text, marker, title, href):
    block = f"<!--{marker}-->[_{md(title)}_]({href})<!--/{marker}-->"
    updated, count = re.subn(rf"<!--{marker}-->.*?<!--/{marker}-->", lambda _: block, text, flags=re.S)
    if not count:
        sys.exit(f"no <!--{marker}--> marker in the README")
    return updated


path = sys.argv[1]
with open(path) as f:
    readme = f.read()
original = readme

try:
    album = fetch("/api/music/latest").get("album")
    if album:
        readme = put(readme, "music", album, "https://paolo.sh/music")
except Exception as error:  # the site is down or changed: keep what's there
    print(f"music: {error}")

try:
    film = fetch("/api/letterboxd/latest").get("title")
    if film:
        readme = put(readme, "movie", film, "https://paolo.sh/movies")
except Exception as error:
    print(f"movie: {error}")

if readme != original:
    with open(path, "w") as f:
        f.write(readme)
    print("updated")
else:
    print("no change")
