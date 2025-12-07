import logging
import numpy as np
from typing import List, Optional, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.repositories.empresa_repo import EmpresaRepository
from app.repositories.match_repo import MatchRepository
from app.models.match import MatchResult
from app.schemas.match import MatchRunCreate

LOGGER = logging.getLogger("match_service")

class MatchService:
    def __init__(self, session: Session):
        self.session = session
        self.empresa_repo = EmpresaRepository(session)
        self.match_repo = MatchRepository(session)

    def _to_np_vec(self, v) -> Optional[np.ndarray]:
        if v is None: return None
        if isinstance(v, list):
            return np.array(v, dtype=np.float32)
        if isinstance(v, str):
            s = v.strip().lstrip("{[").rstrip("}]")
            try:
                nums = [float(x) for x in s.split(",") if x.strip()]
                return np.nan_to_num(np.array(nums, dtype=np.float32))
            except: return None
        return None

    def run_match_inicial(self, nit_empresa: str, top_k: int = 50) -> List[Dict]:
        # 1. Obtener vector de empresa
        company_vecs = self.empresa_repo.get_vector_data(nit_empresa)
        if not company_vecs or not company_vecs.razon_social_embedding:
            LOGGER.warning(f"No vector found for company {nit_empresa}")
            return []

        empresa_vec = self._to_np_vec(company_vecs.razon_social_embedding)
        if empresa_vec is None:
            return []

        # 2. Búsqueda vectorial (Simulada con SQL directo por eficiencia)
        # Asumiendo pgvector instalado y columna objeto_vec en public_licitacion
        query = text(f"""
            SELECT id, entidad, objeto, cuantia, fecha_public, 
                   1 - (objeto_vec <=> :vec) as similarity
            FROM public_licitacion
            WHERE objeto_vec IS NOT NULL
            ORDER BY objeto_vec <=> :vec
            LIMIT :limit
        """)
        
        rows = self.session.execute(query, {"vec": str(empresa_vec.tolist()), "limit": top_k}).fetchall()
        
        results = []
        for row in rows:
            results.append({
                "licitacion_id": row.id,
                "score": float(row.similarity),
                "entidad": row.entidad,
                "objeto": row.objeto,
                "cuantia": float(row.cuantia) if row.cuantia else 0.0,
                "fecha_public": str(row.fecha_public)
            })
            
        return results

    def run_match_augmented(self, nit_empresa: str, top_k: int = 50) -> List[Dict]:
        # 1. Run initial match
        initial_results = self.run_match_inicial(nit_empresa, top_k=top_k * 2) # Get more candidates
        
        # 2. Apply augmented logic (e.g., CIIU matching or keyword boosting)
        # For now, we'll just return initial results as placeholder for complex logic
        # In real implementation, fetch CIIU vectors from Companies and re-rank
        
        return initial_results[:top_k]

    def save_match_run(self, nit_empresa: str, results: List[Dict], filtros: dict = None):
        run = self.match_repo.create_run(MatchRunCreate(
            empresa_nit=nit_empresa,
            filtros_usados=filtros,
            total_encontrados=len(results)
        ))
        
        match_results = []
        for r in results:
            match_results.append(MatchResult(
                run_id=run.run_id,
                licitacion_id=r['licitacion_id'],
                score_similitud=r['score'],
                estado_revision='pendiente'
            ))
        
        self.match_repo.add_results(match_results)
        self.session.commit()
        return run
