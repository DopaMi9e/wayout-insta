"""Runs in GitHub Actions 3x a day: publishes queue/<IST date>/post<slot>.jpg (+ .txt caption) to Instagram.

Instagram API with Instagram Login (graph.instagram.com): create container -> wait FINISHED -> media_publish.
Pictures are served from this public repo's raw URL, which Instagram fetches itself.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.facebook.com/v23.0"
IG_ID = os.environ.get("IG_ID", "17841458801850453")  # thewayout042026
TOKEN = os.environ["IG_TOKEN"]
REPO = os.environ.get("GITHUB_REPOSITORY", "DopaMi9e/wayout-insta")
SLOTS = {2: 1, 8: 2, 16: 3}  # UTC hour -> post number (8:00, 14:00, 22:00 IST)


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}" + ("" if method == "POST" else "?" + data.decode())
    req = urllib.request.Request(url, data if method == "POST" else None, method=method)
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: {e.code} {e.read().decode()[:400]}")


def main():
    now = dt.datetime.now(dt.timezone.utc)
    day = (now + dt.timedelta(hours=5, minutes=30)).date().isoformat()
    if len(sys.argv) > 1 and sys.argv[1]:
        slots = [int(sys.argv[1])]
    else:  # cron runs can start late: take the first due slot not yet posted
        slots = [s for h, s in sorted(SLOTS.items()) if now.hour >= h]
    jpg = next((p for s in slots if (p := Path("queue") / day / f"post{s}.jpg").exists()
                and not p.with_suffix(".done").exists()), None)
    if not jpg:
        print(f"nothing due to post for {day} (slots {slots})")
        return
    done = jpg.with_suffix(".done")
    caption = jpg.with_suffix(".txt").read_text(encoding="utf-8") if jpg.with_suffix(".txt").exists() else ""
    owner, name = REPO.split("/")
    base = f"https://{owner.lower()}.github.io/{name}/"  # GitHub Pages: serves video/mp4 with the right type
    mp4 = jpg.with_suffix(".mp4")
    if mp4.exists():  # reel (cover = the post picture)
        cid = call("POST", f"{IG_ID}/media", media_type="REELS", video_url=base + mp4.as_posix(), caption=caption,
                   cover_url=base + jpg.as_posix(), share_to_feed="true")["id"]
    elif slides := sorted(jpg.parent.glob(f"{jpg.stem}_*.jpg")):  # carousel: post2.jpg + post2_2.jpg ...
        kids = [call("POST", f"{IG_ID}/media", image_url=base + j.as_posix(), is_carousel_item="true")["id"]
                for j in [jpg, *slides]]
        cid = call("POST", f"{IG_ID}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)["id"]
    else:
        cid = call("POST", f"{IG_ID}/media", image_url=base + jpg.as_posix(), caption=caption)["id"]
    for _ in range(60):  # videos take a minute or two to process
        status = call("GET", cid, fields="status_code").get("status_code")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"container {status}")
        time.sleep(5)
    media = call("POST", f"{IG_ID}/media_publish", creation_id=cid)["id"]
    done.write_text(media)
    print(f"posted {jpg} -> media {media}")


if __name__ == "__main__":
    main()
