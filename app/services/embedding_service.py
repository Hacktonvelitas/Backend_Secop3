import os
import google.generativeai as genai
from typing import List
import logging

LOGGER = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            LOGGER.warning("GEMINI_API_KEY not found. Embeddings will fail.")
        else:
            genai.configure(api_key=api_key)

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generates an embedding for the given text using Google's text-embedding-004 model.
        Returns a list of floats (768 dimensions).
        """
        try:
            # text-embedding-004 returns 768 dimensions
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
                title="Company Description" 
            )
            return result['embedding']
        except Exception as e:
            LOGGER.error(f"Error generating embedding: {e}")
            return []
