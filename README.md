# Image optimizer for the web

`optimize_images.py` resizes, strips metadata, fixes EXIF rotation, and re-encodes
images as WebP (default), AVIF, JPEG, or PNG, with optional responsive widths for `srcset`.

```bash
pip install Pillow

# Everything in ./images -> ./optimized as WebP, max 1920px wide
python optimize_images.py images

# Recursive, WebP + AVIF + JPEG fallback, responsive widths
python optimize_images.py images -r -o dist/img -f webp avif jpeg -w 480 960 1600
```

| Option | Default | Description |
|---|---|---|
| `-o, --output` | `optimized` | Output directory (input folder structure is preserved) |
| `-f, --formats` | `webp` | One or more of `webp avif jpeg png` |
| `-q, --quality` | `80` | Quality 1–100 for lossy formats |
| `-m, --max-width` | `1920` | Max width; never upscales |
| `-w, --widths` | — | Generate `name-<W>w.ext` files for each width (overrides `--max-width`) |
| `-r, --recursive` | off | Recurse into subdirectories |
| `--force` | off | Re-process files whose output is already up to date |

Transparent images get a white background when saved as JPEG.
