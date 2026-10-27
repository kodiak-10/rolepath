from io import BytesIO
from pathlib import Path
import platform
import pytest
from rolepath.knowledge import pages_from_upload, save_document, get_documents, search_lexical
from rolepath.ingest import read_upload
from rolepath.db import connect


@pytest.mark.skipif(platform.system()!='Darwin',reason='Requires macOS Vision')
@pytest.mark.parametrize('ext',['png','heic','jpg'])
def test_real_photo_ocr_saved_and_searchable(tmp_path,ext):
    upload=BytesIO((Path(__file__).parent/'fixtures'/f'ocr-note.{ext}').read_bytes())
    upload.name=f'笔记.{ext.upper()}'
    pages=pages_from_upload(upload)
    assert 'GROUP BY' in pages[0][1] and '分组统计' in pages[0][1]
    con=connect(tmp_path/'notes.db')
    save_document(con,upload.name,pages)
    assert len(get_documents(con))==1
    assert search_lexical(con,'GROUP BY 分组')[0].filename==upload.name
    con.close()


def test_image_input_limits_and_corruption():
    from rolepath.image_text import read_image
    with pytest.raises(ValueError,match='5MB'):read_image(b'x'*(5*1024*1024+1),'x.png')
    if platform.system()=='Darwin':
        with pytest.raises(ValueError,match='图片损坏'):read_image(b'invalid image','fake.heic')


def test_jd_upload_uses_same_ocr(monkeypatch):
    from rolepath import ingest
    monkeypatch.setattr(ingest,'read_image',lambda data,name:'识别到的岗位要求')
    f=BytesIO(b'test');f.name='岗位.HEIC'
    assert read_upload(f)=='识别到的岗位要求'
