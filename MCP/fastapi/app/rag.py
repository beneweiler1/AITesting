import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Tuple

class SimpleRAG:
    def __init__(self):
        self.texts: List[str] = []
        self.vectorizer = TfidfVectorizer()
        self.matrix = None
    def add(self, docs: List[str]):
        self.texts.extend(docs)
        self.matrix = self.vectorizer.fit_transform(self.texts)
    def query(self, q: str, k: int = 5) -> List[Tuple[str, float]]:
        if not self.texts:
            return []
        qv = self.vectorizer.transform([q])
        sims = cosine_similarity(qv, self.matrix).ravel()
        idx = np.argsort(-sims)[:k]
        return [(self.texts[i], float(sims[i])) for i in idx]
