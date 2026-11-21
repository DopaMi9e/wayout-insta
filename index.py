"""Writes index.json (last 14 days of the queue: files, caption, posted media id) for the studio website's Instagram page."""
import json
from pathlib import Path

TIMES = {1: "08:00", 2: "14:00", 3: "22:00"}
days = []
for d in sorted((p for p in Path("queue").iterdir() if p.is_dir()), reverse=True)[:14]:
    posts = []
    for jpg in sorted(d.glob("post[0-9].jpg")):
        n = int(jpg.stem[4:])
        txt = jpg.with_suffix(".txt")
        done = jpg.with_suffix(".done")
        slides = [s.as_posix() for s in sorted(d.glob(f"{jpg.stem}_*.jpg"))]
        posts.append({"n": n, "time": TIMES.get(n, "manual"), "image": jpg.as_posix(),
                      "video": jpg.with_suffix(".mp4").as_posix() if jpg.with_suffix(".mp4").exists() else "",
                      "slides": slides, "kind": "reel" if jpg.with_suffix(".mp4").exists() else "carousel" if slides else "post",
                      "caption": txt.read_text(encoding="utf-8").split("\n\n")[0] if txt.exists() else "",
                      "media": done.read_text().strip() if done.exists() else ""})
    days.append({"day": d.name, "posts": posts})
Path("index.json").write_text(json.dumps({"account": "thewayout042026", "days": days}, ensure_ascii=False), encoding="utf-8")
print("index.json:", len(days), "days")
