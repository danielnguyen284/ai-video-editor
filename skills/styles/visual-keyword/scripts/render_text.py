"""Render a static title/keyword PNG with the local FFmpeg; no external API."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from core.common import EditorError, executable


def color(value):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", value):
        raise argparse.ArgumentTypeError("Use #RRGGBB or #RRGGBBAA.")
    return "0x" + value[1:]


def render_text(text_file, output, *, width, height, font_size, font_file,
                foreground, background, outline_color, outline_width):
    text_file, output, font_file = Path(text_file).resolve(), Path(output).resolve(), Path(font_file).resolve()
    if output.exists():
        raise EditorError("Text asset already exists. Choose a new filename to preserve it.")
    if output.suffix.lower() != ".png":
        raise EditorError("Output must be a .png asset.")
    if not font_file.is_file():
        raise EditorError("Font file missing; supply --font-file for an installed bold font.")
    if not all(isinstance(n, int) and 16 <= n <= 4096 for n in (width,height)) or width % 2 or height % 2:
        raise EditorError("Canvas dimensions must be even integers between 16 and 4096.")
    if not 8 <= font_size <= min(width,height) or not 0 <= outline_width <= 32:
        raise EditorError("Font size/outline width is outside the canvas limits.")
    text = text_file.read_text(encoding="utf-8-sig").strip()
    lines = text.splitlines()
    if not 1 <= len(lines) <= 2 or not all(line.strip() for line in lines):
        raise EditorError("Supply one or two nonempty title/keyword lines.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".text-overlay-", dir=output.parent) as temporary:
        temp = Path(temporary).resolve()
        assert temp.is_relative_to(output.parent) and temp != output.parent
        shutil.copy2(font_file, temp/"font.ttf")
        (temp/"text.txt").write_text(text,encoding="utf-8",newline="\n")
        draw = f"drawtext=fontfile=font.ttf:textfile=text.txt:expansion=none:fontsize={font_size}:fontcolor={foreground}:borderw={outline_width}:bordercolor={outline_color}:line_spacing={round(font_size*0.16)}:x=(w-tw)/2:y=(h-th)/2"
        command = [executable("ffmpeg"),"-nostdin","-v","error","-f","lavfi","-i",f"color=c={background}:s={width}x{height}:r=1,format=rgba","-vf",draw,"-frames:v","1","-threads","1", "-n", "text.png"]
        result = subprocess.run(command,cwd=temp,capture_output=True,text=True,encoding="utf-8",errors="replace")
        if result.returncode:
            raise EditorError("Text asset rendering failed:\n"+result.stderr[-4000:])
        # Exclusive creation also preserves an asset created while FFmpeg ran.
        with output.open("xb") as dest, (temp/"text.png").open("rb") as source:
            shutil.copyfileobj(source,dest)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--width", required=True, type=int)
    parser.add_argument("--height", required=True, type=int)
    parser.add_argument("--font-size", required=True, type=int)
    parser.add_argument("--font-file", type=Path, default=Path("C:/Windows/Fonts/arialbd.ttf"))
    parser.add_argument("--color", type=color, default="#FFFFFF")
    parser.add_argument("--background", type=color, default="#00000000")
    parser.add_argument("--outline-color", type=color, default="#101010")
    parser.add_argument("--outline-width", type=int, default=5)
    args=parser.parse_args()
    try:
        print(render_text(args.text_file,args.output,width=args.width,height=args.height,font_size=args.font_size,font_file=args.font_file,foreground=args.color,background=args.background,outline_color=args.outline_color,outline_width=args.outline_width))
    except (EditorError,OSError) as error:
        parser.exit(1,f"ERROR: {error}\n")


if __name__ == "__main__":
    main()
