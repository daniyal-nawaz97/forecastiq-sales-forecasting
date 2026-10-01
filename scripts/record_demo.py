"""Record the 2-3 minute demo video automatically (follows docs/demo-video-script.md).

Needs:  pip install playwright imageio-ffmpeg && playwright install chromium
Start the app (./run.sh) and wait until it's ready, then:
    python -m scripts.record_demo --url http://localhost:8004
Output: docs/demo.mp4 and static/media/demo.webm
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent.parent
CAPTION_JS = """
(text) => {
  let el = document.getElementById('__cap');
  if (!el) {
    el = document.createElement('div'); el.id = '__cap';
    el.style.cssText = 'position:fixed;left:50%;bottom:36px;transform:translateX(-50%);z-index:2147483647;max-width:980px;' +
      'background:rgba(17,24,39,.92);color:#fff;font:600 24px/1.35 Inter,system-ui,sans-serif;padding:16px 26px;border-radius:14px;' +
      'box-shadow:0 10px 40px rgba(0,0,0,.35);text-align:center;transition:opacity .25s;pointer-events:none';
    document.body.appendChild(el);
  }
  el.style.opacity = text ? '1' : '0';
  if (text) el.innerHTML = text;
}
"""


def caption(page, text, ms=3000):
    page.evaluate(CAPTION_JS, text)
    page.wait_for_timeout(ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8004")
    url = ap.parse_args().url
    tmp = Path(tempfile.mkdtemp())
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome") if shutil.which("google-chrome") else p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=str(tmp), record_video_size={"width": 1280, "height": 720})
        page = ctx.new_page()
        page.goto(url + "/#/login"); page.wait_for_timeout(1200)
        caption(page, "How do you decide how much stock to buy for next month?", 3800)
        page.click("#demoBtn"); page.wait_for_timeout(3000)
        caption(page, "Last month, next month's forecast, a realistic range, and how accurate it has been", 4200)
        caption(page, "Solid line = actual sales, dotted = forecast, shaded = likely range. Flags mark Ramadan, Eid and sales", 4500)
        caption(page, "", 100)
        page.goto(url + "/#/forecast?product=Premium%20Dates%20500g&horizon=6&view=weekly&history=24"); page.wait_for_timeout(3000)
        caption(page, "Any product, category or branch. Dates jump every Ramadan, and the forecast knows it", 4200)
        page.select_option("#fb", "Karachi (Clifton)"); page.wait_for_timeout(2500)
        caption(page, "Filter by branch: the chart updates instantly", 3000)
        caption(page, "", 100)
        page.goto(url + "/#/"); page.wait_for_timeout(2000)
        page.mouse.wheel(0, 700); page.wait_for_timeout(800)
        caption(page, "Attention: what may run short, what's overstocked, which branch is slipping", 4500)
        caption(page, "", 100)
        page.goto(url + "/#/scenarios"); page.wait_for_timeout(2000)
        for v in (5, 10, 15):
            page.eval_on_selector("#s_discount", f"(s) => {{ s.value = {v}; s.dispatchEvent(new Event('input')); }}")
            page.wait_for_timeout(500)
        page.wait_for_timeout(1200)
        caption(page, "What if we give 15% off? More revenue, but see what happens to margin", 4800)
        caption(page, "", 100)
        page.goto(url + "/#/accuracy"); page.wait_for_timeout(2500)
        caption(page, "Here's how well we would have predicted your past months, using only earlier data", 4500)
        caption(page, "", 100)
        page.goto(url + "/#/reports"); page.wait_for_timeout(2500)
        caption(page, "One-click monthly report: PDF for the manager, Excel for finance, a short email", 4000)
        results = BASE / "docs" / "results.json"
        if results.exists():
            s = json.loads(results.read_text())["summary"]
            caption(page, f"Demo business (sample data): {s['accuracy']}% accurate on the last {s['months_tested']} months, "
                          f"{round(s['improvement'] * 100)}% better than a simple guess", 5000)
        caption(page, "Send me 12 months of your sales in Excel, and I'll show you a forecast for your own business", 4500)
        video = page.video.path()
        ctx.close(); browser.close()
    out = BASE / "static" / "media" / "demo.webm"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(video, out)
    try:
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-movflags", "+faststart", str(BASE / "docs" / "demo.mp4")], check=True)
        print("Saved docs/demo.mp4 and static/media/demo.webm")
    except Exception as e:
        print("Saved static/media/demo.webm (mp4 skipped:", e, ")")


if __name__ == "__main__":
    main()
