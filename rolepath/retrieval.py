"""Independent retrieval interfaces: local lexical baseline vs real vector search."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class SearchHit:
    resource: dict
    score: float
    method: str


def describe(r: dict) -> str:
    return f"{r['title']} 技能：{'、'.join(r['skills'])} 难度：{r['difficulty']} 类型：{r['type']} 摘要：{r['description']}"

class LexicalRetriever:
    """Works offline, but explicitly is NOT dense embedding RAG."""
    def __init__(self, resources: list[dict]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.resources = resources
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 4))
        self.matrix = self.vectorizer.fit_transform([describe(r) for r in resources])

    def search(self, query: str, limit: int = 3, skill: str | None = None) -> list[SearchHit]:
        from sklearn.metrics.pairwise import cosine_similarity
        values = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        # Exact skill tags act as a guard against an irrelevant embedding match.
        candidates = [i for i, r in enumerate(self.resources) if not skill or skill in r['skills']]
        candidates.sort(key=lambda i: values[i], reverse=True)
        return [SearchHit(self.resources[i], float(values[i]), 'TF-IDF 字符 n-gram（非向量 Embedding）') for i in candidates[:limit]]

class DenseRetriever:
    """Actual BGE embeddings + Chroma persistent vector storage."""
    def __init__(self, resources: list[dict], persist_path: str = '.rolepath_chroma', model_name: str = 'BAAI/bge-small-zh-v1.5'):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError('缺少真实向量检索依赖：pip install -r requirements-vectors.txt') from e
        self.resources = {r['id']: r for r in resources}
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.client = chromadb.PersistentClient(path=str(Path(persist_path)))
        self.collection = self.client.get_or_create_collection('rolepath_resources_v1', metadata={"hnsw:space": "cosine"})
        documents = [describe(r) for r in resources]
        self.collection.upsert(
            ids=[r['id'] for r in resources],
            documents=documents,
            metadatas=[{"skill_names": '|'.join(r['skills'])} for r in resources],
            embeddings=self.model.encode(documents, normalize_embeddings=True, show_progress_bar=False).tolist(),
        )

    def search(self, query: str, limit: int = 3, skill: str | None = None) -> list[SearchHit]:
        if not query.strip():
            return []
        if skill:
            # Query all candidates and filter exact tag, rather than SQL-like substring filters.
            n = len(self.resources)
        else:
            n = min(limit, len(self.resources))
        emb = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False).tolist()
        response = self.collection.query(query_embeddings=emb, n_results=n, include=['distances'])
        hits = []
        for rid, distance in zip(response['ids'][0], response['distances'][0]):
            r = self.resources.get(rid)
            if r is not None and (not skill or skill in r['skills']):
                hits.append(SearchHit(r, max(0.0, 1.0 - float(distance)), 'BGE Embedding + Chroma cosine'))
        return hits[:limit]


def build_retriever(resources: list[dict], mode='lexical'):
    if mode == 'dense':
        return DenseRetriever(resources, persist_path=os.getenv('CHROMA_PATH', '.rolepath_chroma'), model_name=os.getenv('EMBEDDING_MODEL', 'BAAI/bge-small-zh-v1.5'))
    return LexicalRetriever(resources)
