from app import process_uploaded_image, read_png_metadata
from io import BytesIO
from PIL import Image
import os


def make_filelike(tmp_path, name='test.png'):
    p = tmp_path / 'src.png'
    img = Image.new('RGBA', (60, 40), (200, 100, 50, 255))
    img.save(p, format='PNG')
    b = p.read_bytes()
    bio = BytesIO(b)
    bio.seek(0)
    bio.filename = name
    return bio


def test_process_uploaded_image_writes_files_and_metadata(tmp_path):
    fileobj = make_filelike(tmp_path)
    wm_rel, orig_rel = process_uploaded_image(fileobj, 'tester', prefix='example', save_original=True, author_name='Alice Tester - tester')

    # paths are relative to static/
    static_root = os.path.join(os.getcwd(), 'static')
    wm_full = os.path.join(static_root, wm_rel.replace('/', os.sep))
    orig_full = os.path.join(static_root, orig_rel.replace('/', os.sep))

    assert os.path.exists(wm_full), "Watermarked file should exist"
    assert os.path.exists(orig_full), "Original file should exist"

    md = read_png_metadata(orig_full)
    assert md.get('Author') == 'Alice Tester - tester'
    assert md.get('Uploaded on Beevy') is not None

    # cleanup created files
    try:
        os.remove(wm_full)
        os.remove(orig_full)
    except Exception:
        pass
