"""Local document RAG: text/PDF chunking, SQLite metadata, lexical or dense retrieval."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import io
import re
import sqlite3
import uuid
from .image_text import is_image, read_image

@dataclass
class ChunkHit:
    id: str
    filename: str
    page: int
    text: str
    score: float
    method: str


def pages_from_upload(upload) -> list[tuple[int,str]]:
    data = upload.getvalue()
    if not data or len(data) > 5 * 1024 * 1024:
        raise ValueError('文件为空或超过 5MB')
    if is_image(upload.name):
        return [(1, read_image(data, upload.name))]
    if upload.name.lower().endswith(('.md','.txt')):
        return [(1, data.decode('utf-8-sig'))]
    if upload.name.lower().endswith('.pdf'):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 40:
            raise ValueError('最多 40 页 PDF')
        return [(i+1, p.extract_text() or '') for i,p in enumerate(reader.pages)]
    raise ValueError('支持 TXT/MD/PDF/PNG/JPG/HEIC/HEIF')


def chunk_page(text: str, size: int = 500, overlap: int = 80) -> list[str]:
    """Character chunks preserve overlap. Designed for teaching, not token-perfect splitting."""
    if size < 100 or overlap < 0 or overlap >= size:
        raise ValueError('chunk 参数无效')
    clean = re.sub(r'[ \t]+', ' ', text).strip()
    if not clean:
        return []
    step = size - overlap
    result = []
    for start in range(0, len(clean), step):
        snippet = clean[start:start+size]
        if len(snippet.strip()) >= 15:
            result.append(snippet)
        if start + size >= len(clean):
            break
    return result


def ensure_schema(conn: sqlite3.Connection):
    if getattr(conn,'cloud',False): return
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, filename TEXT NOT NULL, checksum TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, filename TEXT NOT NULL, page INTEGER NOT NULL, chunk_no INTEGER NOT NULL, content TEXT NOT NULL);
    ''')


def save_document(conn, filename: str, pages: list[tuple[int,str]]) -> tuple[str,int]:
    ensure_schema(conn)
    raw = '\n'.join(t for _,t in pages)
    checksum = hashlib.sha256((filename + '\n' + raw).encode('utf-8')).hexdigest()
    if getattr(conn,'cloud',False):
        chunks = [dict(page=page,chunk_no=i,content=part) for page,text in pages for i,part in enumerate(chunk_page(text))]
        if not chunks: raise ValueError('没有可用文字，未保存文件。')
        return conn.save_document(filename,checksum,chunks)
    old = conn.execute('SELECT id FROM documents WHERE checksum=?',(checksum,)).fetchone()
    if old:
        return old['id'], 0
    docid=str(uuid.uuid4())
    chunks=[]
    for page, content in pages:
        for i, fragment in enumerate(chunk_page(content)):
            chunks.append((f'{docid}:{page}:{i}',docid,filename,page,i,fragment))
    if not chunks:
        raise ValueError('没有可用文本，扫描版 PDF 暂不支持')
    with conn:
        conn.execute('INSERT INTO documents(id,filename,checksum) VALUES(?,?,?)',(docid,filename,checksum))
        conn.executemany('INSERT INTO chunks(id,document_id,filename,page,chunk_no,content) VALUES(?,?,?,?,?,?)',chunks)
    return docid,len(chunks)


def get_documents(conn):
    if getattr(conn,'cloud',False): return conn.get_documents()
    ensure_schema(conn)
    return list(conn.execute('SELECT * FROM documents ORDER BY created_at DESC'))


def get_chunks(conn):
    if getattr(conn,'cloud',False): return conn.get_chunks()
    ensure_schema(conn)
    return list(conn.execute('SELECT * FROM chunks ORDER BY rowid'))


def delete_document(conn, docid:str):
    if getattr(conn,'cloud',False): return conn.delete_document(docid)
    ensure_schema(conn)
    with conn:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='note_reports'").fetchone():
            import json
            for row in list(conn.execute('SELECT id,payload FROM note_reports')):
                if any(source['document_id'] == docid for source in json.loads(row['payload'])['sources']):
                    conn.execute('DELETE FROM note_reports WHERE id=?', (row['id'],))
        conn.execute('DELETE FROM documents WHERE id=?',(docid,))


def search_lexical(conn, question: str, top_k:int=4) -> list[ChunkHit]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    rows=get_chunks(conn)
    if not rows or not question.strip():
        return []
    documents=[row['content'] for row in rows]
    tfidf=TfidfVectorizer(analyzer='char',ngram_range=(2,4))
    matrix=tfidf.fit_transform(documents)
    scores=cosine_similarity(tfidf.transform([question]),matrix)[0]
    order=sorted(range(len(rows)),key=lambda i:scores[i],reverse=True)
    # Weak lexical overlap is not sufficient evidence.
    return [ChunkHit(rows[i]['id'],rows[i]['filename'],rows[i]['page'],rows[i]['content'],float(scores[i]),'TF-IDF（非 Embedding）') for i in order[:top_k] if scores[i] >= .025]


def search_dense(conn, question: str, dense_retriever, top_k:int=4) -> list[ChunkHit]:
    """Reconcile Chroma document collection with SQLite; reuse already loaded BGE model."""
    rows=get_chunks(conn)
    col=dense_retriever.client.get_or_create_collection(('rolepath_docs_'+conn.user_id) if getattr(conn,'cloud',False) else 'rolepath_user_docs_v1',metadata={'hnsw:space':'cosine'})
    actual=set(col.get(include=[])['ids'])
    desired={r['id'] for r in rows}
    if actual - desired:
        col.delete(ids=sorted(actual-desired))
    if not rows or not question.strip():
        return []
    missing=[r for r in rows if r['id'] not in actual]
    for i in range(0,len(missing),30):
        batch=missing[i:i+30]
        embeddings=dense_retriever.model.encode([r['content'] for r in batch],normalize_embeddings=True,show_progress_bar=False).tolist()
        col.upsert(ids=[r['id'] for r in batch], documents=[r['content'] for r in batch], embeddings=embeddings,
                   metadatas=[{'filename':r['filename'],'page':r['page']} for r in batch])
    result=col.query(query_embeddings=dense_retriever.model.encode([question],normalize_embeddings=True).tolist(),
                     n_results=min(top_k,len(rows)),include=['documents','metadatas','distances'])
    hits=[]
    for rid,doc,meta,dist in zip(result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0]):
        score=max(0.0,1.0-float(dist))
        # Conservative score threshold for MVP, not a calibrated certainty estimate.
        if score < .18:
            continue
        hits.append(ChunkHit(rid,str(meta['filename']),int(meta['page']),doc,score,'BGE Embedding + Chroma'))
    return hits
