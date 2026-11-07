"""Independent draft jobs and a local side-by-side viewer; no automatic edit or approval."""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

from core.common import EditorError, ROOT, digest, identifier, read_json, resolve_profile, timestamp, write_json
from core.jobs import create_job


def create_comparison(comparison_id, video, profiles, brief, output_format):
    identifier(comparison_id)
    if not 2 <= len(profiles) <= 6 or len(set(profiles)) != len(profiles):
        raise EditorError("Choose 2–6 different profiles for a comparison.")
    if output_format not in ("vertical", "horizontal"):
        raise EditorError("Choose vertical or horizontal output explicitly.")
    source = Path(video).resolve()
    if not source.is_file():
        raise EditorError(f"Source video not found: {source}")
    folder = ROOT / "comparisons" / comparison_id
    if folder.exists():
        raise EditorError("Comparison already exists. Choose another ID; existing outputs are preserved.")
    variants = []
    for index, profile_id in enumerate(profiles):
        config = resolve_profile(profile_id)
        job_id = identifier(f"{comparison_id}-{chr(97 + index)}")
        if (ROOT / "jobs" / job_id).exists():
            raise EditorError(f"Job already exists: {job_id}")
        variants.append({"label": chr(65 + index), "job_id": job_id, "profile": profile_id,
                         "group": config["profile"].get("skill_group"), "status": "pending"})
    width, height = (1080, 1920) if output_format == "vertical" else (1920, 1080)
    output = {"width": width, "height": height, "fps": 30, "fit": "pad"}
    manifest = {"schema_version": "1.0", "id": comparison_id, "created_at": timestamp(),
                "source_sha256": digest(source), "brief": brief, "output": output,
                "status": "creating", "variants": variants,
                "note": "Initial full-length drafts only. Creative choices, actual edits and export are still pending."}
    folder.mkdir(parents=True)
    write_json(folder / "comparison.json", manifest)
    try:
        for variant in variants:
            job = create_job(variant["job_id"], source, variant["profile"], brief, output=output)
            if digest(job / read_json(job / "job.json")["assets"][0]["path"]) != manifest["source_sha256"]:
                raise EditorError("Input changed during copying. Preserved partial drafts; inspect before continuing.")
            variant["status"] = "draft"
            write_json(folder / "comparison.json", manifest, replace=True)
        manifest["status"] = "drafts"
    except Exception:
        manifest["status"] = "partial"
        write_json(folder / "comparison.json", manifest, replace=True)
        raise
    write_json(folder / "comparison.json", manifest, replace=True)
    comparison_view(comparison_id)
    return folder


def comparison_view(comparison_id):
    identifier(comparison_id)
    folder = ROOT / "comparisons" / comparison_id
    manifest = read_json(folder / "comparison.json")
    cards = []
    for variant in manifest["variants"]:
        job_id = identifier(variant["job_id"])
        revisions = [p for p in (ROOT / "jobs" / job_id / "revisions").glob("r[0-9]*")
                     if re.fullmatch(r"r\d{3,}", p.name) and (p / "renders/video.mp4").is_file()]
        label = html.escape(variant["label"] + " · " + variant["profile"])
        if revisions:
            revision = max(revisions, key=lambda p: int(p.name[1:]))
            target = "../../" + (revision / "renders/video.mp4").relative_to(ROOT).as_posix()
            video = f'<video controls preload="metadata" src="{quote(target, safe="/.")}" {"muted" if cards else ""}></video><p>{html.escape(revision.name)} · <a href="{quote(target, safe="/.")}">Mở MP4</a></p>'
        else:
            video = '<p class="pending">Chưa có bản xuất. Dựng và xuất job này rồi chạy compare-view để cập nhật.</p>'
        cards.append(f'<article><h2>{label}</h2><p>Job: {html.escape(job_id)}</p>{video}</article>')
    page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>So sánh bản dựng</title><style>body{font:16px system-ui;background:#101318;color:#e9eef4;margin:28px}h1{font-size:25px}h2{font-size:17px}a{color:#9ccaff}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}article{background:#1b222c;padding:20px;border-radius:12px}video{width:100%;max-height:68vh;background:#000}.pending{padding:40px 0;color:#bec7d2}button{font:inherit;padding:10px 16px;margin:0 12px 18px 0;cursor:pointer}small{display:block;color:#bbc5d1;margin:14px 0}</style>
<h1>So sánh bản dựng — ''' + html.escape(comparison_id) + '''</h1><p>''' + html.escape(manifest["brief"]) + '''</p>
<button id="play">Phát tất cả từ đầu</button><button id="pause">Dừng tất cả</button><small>Mở file HTML này trực tiếp trên máy. Chỉ video đầu bật tiếng mặc định. Phát cùng mốc thời gian; các bản có cut khác nhau không tự căn theo cùng câu nói. Không tự chọn bản thắng.</small><main>''' + "".join(cards) + '''</main>
<script>const vs=[...document.querySelectorAll('video')];document.getElementById('play').onclick=()=>{for(const v of vs)v.currentTime=0;Promise.allSettled(vs.map(v=>v.play()))};document.getElementById('pause').onclick=()=>vs.forEach(v=>v.pause());</script></html>'''
    target = folder / "index.html"
    target.write_text(page, encoding="utf-8")
    return target
