#!/usr/bin/env python3
"""Dung video ghep anh + phu de + giong doc bang FFmpeg, tai len link ky.
Khong chua khoa bi mat. Link spec/upload do n8n cua Nhip cap, het han sau 1 gio."""
import json, os, subprocess, sys, urllib.request

SPEC_URL = os.environ["SPEC_URL"]
UPLOAD_URL = os.environ["UPLOAD_URL"]
W, H = (1080, 1920)

def get(url, path):
    with urllib.request.urlopen(url, timeout=120) as r, open(path, "wb") as f:
        f.write(r.read())

def sh(*args):
    subprocess.run(args, check=True)

def ts(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

get(SPEC_URL, "spec.json")
spec = json.load(open("spec.json", encoding="utf-8"))
if spec.get("aspect") == "16:9":
    W, H = 1920, 1080
elif spec.get("aspect") == "1:1":
    W, H = 1080, 1080
scenes = spec["scenes"][:12]
clips, srt, t0 = [], [], 0.0
for i, s in enumerate(scenes):
    d = max(2.0, min(float(s.get("duration", 4)), 10.0))
    get(s["image_url"], f"img{i}.jpg")
    frames = int(d * 25)
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='min(zoom+0.0006,1.15)':d={frames}:s={W}x{H}:fps=25,format=yuv420p")
    sh("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", f"img{i}.jpg",
       "-vf", vf, "-t", str(d), "-an", f"clip{i}.mp4")
    clips.append(f"clip{i}.mp4")
    if s.get("text"):
        srt.append(f"{len(srt)+1}\n{ts(t0)} --> {ts(t0+d-0.1)}\n{s['text']}\n")
    t0 += d
open("list.txt", "w").write("".join(f"file '{c}'\n" for c in clips))
open("sub.srt", "w", encoding="utf-8").write("\n".join(srt))
sh("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "silent.mp4")

style = f"FontName=DejaVu Sans,Bold=1,FontSize={20 if W<H else 18},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV={int(H*0.12)}"
vf = f"subtitles=sub.srt:force_style='{style}'" if srt else "null"
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", "silent.mp4"]
if spec.get("audio_url"):
    get(spec["audio_url"], "voice.mp3")
    cmd += ["-i", "voice.mp3", "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-shortest"]
cmd += ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-movflags", "+faststart", "out.mp4"]
sh(*cmd)

req = urllib.request.Request(UPLOAD_URL, data=open("out.mp4", "rb").read(), method="PUT",
                             headers={"Content-Type": "video/mp4"})
urllib.request.urlopen(req, timeout=300).read()
print("Da tai video len, kich thuoc", os.path.getsize("out.mp4"))
