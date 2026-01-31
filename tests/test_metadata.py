import os
from datetime import datetime
from PIL import Image
from app import watermark_text_with_metadata, read_png_metadata, add_metadata


def test_watermark_and_metadata_roundtrip(tmp_path):
    src = tmp_path / "src.jpg"
    dst = tmp_path / "dst.png"

    # create a sample JPEG source image
    Image.new('RGB', (100, 100), color=(255, 0, 0)).save(str(src), format='JPEG')

    metadata = {
        "Author": "Test Author",
        "Uploaded on Beevy": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # run the watermark + metadata writer
    watermark_text_with_metadata(str(src), str(dst), "Watermark", metadata)

    # read back metadata and assert
    md = read_png_metadata(str(dst))
    assert md.get("Author") == "Test Author"
    assert md.get("Uploaded on Beevy") == metadata["Uploaded on Beevy"]


def test_add_metadata_on_png(tmp_path):
    p = tmp_path / "img.png"

    # create a sample PNG and add metadata via add_metadata
    Image.new('RGBA', (50, 50), color=(0, 255, 0, 255)).save(str(p), format='PNG')

    add_metadata(str(p), "Alice", datetime.now())

    md = read_png_metadata(str(p))
    assert md.get("Author") == "Alice"
    assert md.get("Downloaded from Beevy") is not None
