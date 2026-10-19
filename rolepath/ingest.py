"""Parse user-owned text files as project evidence, not authoritative skill verification."""
from __future__ import annotations
from .image_text import is_image, read_image

def read_upload(upload) -> str:
    data=upload.getvalue()
    if len(data)>5*1024*1024:
        raise ValueError('单文件最多 5MB')
    name=upload.name.lower()
    if is_image(name):
        return read_image(data, name)
    if name.endswith(('.txt','.md')):
        return data.decode('utf-8-sig')
    if name.endswith('.pdf'):
        from pypdf import PdfReader
        import io
        reader=PdfReader(io.BytesIO(data))
        if len(reader.pages)>40:
            raise ValueError('单份PDF最多40页')
        return '\n'.join((page.extract_text() or '') for page in reader.pages)
    raise ValueError('支持 PDF / TXT / Markdown / PNG / JPG / HEIC / HEIF')
