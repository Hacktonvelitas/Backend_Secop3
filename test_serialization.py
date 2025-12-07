import numpy as np
from dataclasses import dataclass, asdict
from typing import Optional

# Mocking the classes to match the file content I read

@dataclass
class MatchResult:
    licitacion_id: int
    score: float          
    best_chunk_text: str  
    entidad: str
    objeto: str
    cuantia: float        
    fecha_public: str     
    cluster_id: int = -1
    vector_licitacion: Optional[np.ndarray] = None 

    def to_dict(self):
        d = asdict(self)
        if 'vector_licitacion' in d:
             del d['vector_licitacion']
        return d

@dataclass
class AugmentedMatchResult:
    base_match: MatchResult
    ai_score: float = 0.0          
    final_score: float = 0.0       
    ai_explanation: str = ""       
    cumple_requisitos: bool = True 

    def to_dict(self):
        d = asdict(self)
        # Manually convert base_match using its own to_dict to handle numpy arrays
        if self.base_match:
             d['base_match'] = self.base_match.to_dict()
        return d

def test():
    vec = np.array([0.1, 0.2], dtype=np.float32)
    m = MatchResult(
        licitacion_id=123,
        score=0.9,
        best_chunk_text="text",
        entidad="ent",
        objeto="obj",
        cuantia=100.0,
        fecha_public="2024-01-01",
        vector_licitacion=vec
    )
    
    aug = AugmentedMatchResult(base_match=m)
    
    print("Testing MatchResult.to_dict()...")
    d_m = m.to_dict()
    if 'vector_licitacion' in d_m:
        print("FAIL: vector_licitacion present in MatchResult dict")
    else:
        print("PASS: vector_licitacion removed from MatchResult dict")
        
    print("Testing AugmentedMatchResult.to_dict()...")
    d_aug = aug.to_dict()
    
    base = d_aug.get('base_match')
    if 'vector_licitacion' in base:
        print("FAIL: vector_licitacion present in AugmentedMatchResult dict")
        print(base['vector_licitacion'])
    else:
        print("PASS: vector_licitacion removed from AugmentedMatchResult dict")

    import json
    try:
        json.dumps(d_aug)
        print("PASS: JSON serialization successful")
    except Exception as e:
        print(f"FAIL: JSON serialization failed: {e}")

if __name__ == "__main__":
    test()
