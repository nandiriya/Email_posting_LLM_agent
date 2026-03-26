from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

class SimpleRAG:
    def __init__(self):
        self.text_chunks = []
        self.index = None

    def chunk_text(self, text, chunk_size=300):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)
        return chunks

    def build_index(self, text):
        self.text_chunks = self.chunk_text(text)

        embeddings = model.encode(self.text_chunks)
        embeddings = np.array(embeddings).astype("float32")

        self.index = faiss.IndexFlatL2(embeddings.shape[1])
        self.index.add(embeddings)

    def retrieve(self, query, k=3):
        query_vec = model.encode([query]).astype("float32")
        distances, indices = self.index.search(query_vec, k)

        results = [self.text_chunks[i] for i in indices[0]]
        return "\n\n".join(results)