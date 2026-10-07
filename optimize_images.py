#!/usr/bin/env python3
"""Optimize images for the web.

Resizes, strips metadata, fixes EXIF rotation, and re-encodes images as
WebP (default), AVIF, JPEG, and/or PNG. Can also generate multiple widths
for responsive <img srcset> usage.

Examples:
    # Optimize everything in ./images into ./optimized as WebP, max 1920px wide
    python optimize_images.py images

    # WebP + AVIF + JPEG fallback, responsive widths, custom output dir
    python optimize_images.py images -o dist/img -f webp avif jpeg -w 480 960 1600

    # Single file, higher quality
    python optimize_images.py hero.png -q 90

Requires Pillow:  pip install Pillow
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps, features
except ImportError:
    sys.exit("Pillow is required: pip install Pillow")

INPUT_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp", ".gif", ".avif"}
OUTPUT_EXTS = {"webp": ".webp", "avif": ".avif", "jpeg": ".jpg", "png": ".png"}


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def find_images(paths, recursive):
    for p in paths:
        p = Path(p)
        if p.is_file() and p.suffix.lower() in INPUT_EXTS:
            yield p, p.parent
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for f in sorted(p.glob(pattern)):
                if f.is_file() and f.suffix.lower() in INPUT_EXTS:
                    yield f, p


def prepare(img: Image.Image, fmt: str) -> Image.Image:
    """Convert to a mode the target format supports."""
    has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
    if fmt == "jpeg":
        if has_alpha:
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.getchannel("A"))
            return bg
        return img.convert("RGB")
    if fmt == "png":
        return img if img.mode in ("RGB", "RGBA", "L", "LA", "P") else img.convert("RGBA" if has_alpha else "RGB")
    # webp / avif
    return img.convert("RGBA" if has_alpha else "RGB")


def save(img: Image.Image, dest: Path, fmt: str, quality: int):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "webp":
        img.save(dest, "WEBP", quality=quality, method=6)
    elif fmt == "avif":
        img.save(dest, "AVIF", quality=quality, speed=4)
    elif fmt == "jpeg":
        img.save(dest, "JPEG", quality=quality, optimize=True, progressive=True)
    elif fmt == "png":
        img.save(dest, "PNG", optimize=True)


def process(src: Path, base: Path, args) -> tuple[int, int]:
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)  # apply rotation, then metadata is dropped on save
        im.load()

    if args.widths:
        # Never upscale: drop widths larger than the source, keep the source width instead.
        widths = sorted({min(w, im.width) for w in args.widths})
    else:
        widths = [args.max_width]
    orig_size = src.stat().st_size
    written = 0
    rel = src.relative_to(base).with_suffix("")

    for w in widths:
        if im.width > w:
            h = round(im.height * w / im.width)
            resized = im.resize((w, h), Image.LANCZOS)
        else:
            resized = im
        suffix = f"-{w}w" if args.widths else ""

        for fmt in args.formats:
            dest = args.output / f"{rel}{suffix}{OUTPUT_EXTS[fmt]}"
            if not args.force and dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
                print(f"  skip  {dest} (up to date)")
                written += dest.stat().st_size
                continue
            save(prepare(resized, fmt), dest, fmt, args.quality)
            size = dest.stat().st_size
            written += size
            print(f"  {fmt:<5} {dest}  {resized.width}x{resized.height}  "
                  f"{human(size)} ({size / orig_size:.0%} of original)")
    return orig_size, written


def main():
    ap = argparse.ArgumentParser(description="Optimize images for the web.")
    ap.add_argument("inputs", nargs="+", help="image files and/or directories")
    ap.add_argument("-o", "--output", type=Path, default=Path("optimized"), help="output directory (default: ./optimized)")
    ap.add_argument("-f", "--formats", nargs="+", choices=OUTPUT_EXTS, default=["webp"], help="output formats (default: webp)")
    ap.add_argument("-q", "--quality", type=int, default=80, help="quality 1-100 for lossy formats (default: 80)")
    ap.add_argument("-m", "--max-width", type=int, default=1920, help="max width in px, never upscales (default: 1920)")
    ap.add_argument("-w", "--widths", type=int, nargs="+", help="generate these widths for srcset (overrides --max-width)")
    ap.add_argument("-r", "--recursive", action="store_true", help="recurse into subdirectories")
    ap.add_argument("--force", action="store_true", help="re-process even if output is up to date")
    args = ap.parse_args()

    if not 1 <= args.quality <= 100:
        ap.error("--quality must be between 1 and 100")
    if "avif" in args.formats and not features.check("avif"):
        ap.error("this Pillow build lacks AVIF support; upgrade Pillow (>= 11.2) or drop 'avif'")

    total_in = total_out = count = 0
    for src, base in find_images(args.inputs, args.recursive):
        print(src)
        try:
            i, o = process(src, base, args)
        except Exception as e:  # keep going on bad files
            print(f"  error: {e}", file=sys.stderr)
            continue
        total_in += i
        total_out += o
        count += 1

    if not count:
        sys.exit("No images found.")
    print(f"\nProcessed {count} image(s): {human(total_in)} in -> {human(total_out)} out")


if __name__ == "__main__":
    main()
