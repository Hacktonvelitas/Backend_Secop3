from __future__ import annotations
import logging
import numpy as np
from typing import List, Optional, Dict, Tuple
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.repositories.empresa_repo import EmpresaRepository
from app.repositories.match_repo import MatchRepository
from app.models.match import MatchResult as MatchResultModel
from app.schemas.match import MatchRunCreate

LOGGER = logging.getLogger("match_service")

class MatchService:
    def __init__(self, session: Session):
        self.session = session
        self.empresa_repo = EmpresaRepository(session)
        self.match_repo = MatchRepository(session)

    def _fetch_empresa_vector(self, nit: str) -> Optional[str]:
        clean_nit = nit.replace("-", "").replace(" ", "")
        # Try empresa_info (1536)
        try:
            sql = text("SELECT razon_social_vec FROM public.empresa_info WHERE nit = :nit")
            row = self.session.execute(sql, {"nit": clean_nit}).fetchone()
            if row and row[0] is not None:
                 return row[0]
        except Exception as e:
            LOGGER.warning(f"Error fetching from empresa_info: {e}")

        # Try companies (768) - WARNING: Dimension mismatch if comparing with 1536
        try:
            sql2 = text("SELECT razon_social_embedding FROM public.companies WHERE nit = :nit")
            row2 = self.session.execute(sql2, {"nit": clean_nit}).fetchone()
            if row2 and row2[0] is not None:
                return row2[0]
        except Exception as e:
             LOGGER.warning(f"Error fetching from companies: {e}")
        
        return None

    def run_match_inicial(
        self, 
        nit_empresa: str, 
        top_k: int = 50,
        min_score: float = 0.6,
        fecha_inicio: Optional[date] = None,
        location_filter: Optional[str] = None,
        sector_keywords: Optional[List[str]] = None,
        exclusion_keywords: Optional[List[str]] = None,
        min_cuantia: Optional[float] = None,
        max_cuantia: Optional[float] = None
    ) -> List[Dict]:
        
        empresa_vec_str = self._fetch_empresa_vector(nit_empresa)
        if not empresa_vec_str:
            LOGGER.warning(f"No vector found for company {nit_empresa}")
            return []

        # Build Query
        where_clauses = ["c.embedding_vec IS NOT NULL"]
        params = {
            "query_vec": empresa_vec_str, 
            "limit": top_k,
            "min_sim": min_score
        }

        if fecha_inicio:
            where_clauses.append("l.fecha_public >= :fecha_inicio")
            params["fecha_inicio"] = fecha_inicio

        if location_filter:
            where_clauses.append("l.ubicacion ILIKE :loc")
            params["loc"] = f"%{location_filter}%"

        if min_cuantia:
            where_clauses.append("l.cuantia >= :min_cuantia")
            params["min_cuantia"] = min_cuantia
        if max_cuantia:
            where_clauses.append("l.cuantia <= :max_cuantia")
            params["max_cuantia"] = max_cuantia

        if sector_keywords:
            or_conds = []
            for i, kw in enumerate(sector_keywords):
                key = f"kw_inc_{i}"
                or_conds.append(f"(l.act_econ ILIKE :{key} OR l.objeto ILIKE :{key})")
                params[key] = f"%{kw}%"
            if or_conds:
                where_clauses.append(f"({' OR '.join(or_conds)})")

        if exclusion_keywords:
            for i, kw in enumerate(exclusion_keywords):
                key = f"kw_exc_{i}"
                where_clauses.append(f"l.objeto NOT ILIKE :{key}")
                where_clauses.append(f"c.chunk_text NOT ILIKE :{key}") 
                params[key] = f"%{kw}%"

        sql = f"""
            SELECT 
                c.licitacion_id,
                c.chunk_text,
                (1 - (c.embedding_vec <=> :query_vec)) as similarity,
                l.entidad,
                l.objeto,
                l.cuantia,
                l.fecha_public
            FROM public.public_licitacion_chunk c
            JOIN public.public_licitacion l ON c.licitacion_id = l.id
            WHERE {" AND ".join(where_clauses)}
              AND (1 - (c.embedding_vec <=> :query_vec)) >= :min_sim
            ORDER BY similarity DESC
            LIMIT :limit
        """
        
        rows = self.session.execute(text(sql), params).fetchall()
        
        results = []
        seen_ids = set()
        for row in rows:
            if row.licitacion_id in seen_ids:
                continue
            seen_ids.add(row.licitacion_id)
            
            results.append({
                "licitacion_id": row.licitacion_id,
                "score": float(row.similarity),
                "best_chunk_text": row.chunk_text,
                "entidad": row.entidad,
                "objeto": row.objeto,
                "cuantia": float(row.cuantia) if row.cuantia else 0.0,
                "fecha_public": str(row.fecha_public)
            })
            
        return results

    def _mock_llm_analysis(self, nit_empresa: str, match: Dict) -> Tuple[float, str, bool]:
        # Mock LLM
        ai_score = 0.7 
        if match['cuantia'] > 500_000_000:
            ai_score = 0.9
        explanation = "Análisis IA: El objeto parece compatible con el sector de la empresa."
        return ai_score, explanation, True

    def run_match_augmented(
        self, 
        nit_empresa: str, 
        top_k: int = 10,
        min_score_inicial: float = 0.5,
        fecha_inicio: Optional[date] = None,
        location_filter: Optional[str] = None,
        sector_keywords: Optional[List[str]] = None,
        exclusion_keywords: Optional[List[str]] = None,
        min_cuantia: Optional[float] = None,
        max_cuantia: Optional[float] = None
    ) -> List[Dict]:
        
        candidates = self.run_match_inicial(
            nit_empresa=nit_empresa,
            top_k=top_k * 3,
            min_score=min_score_inicial,
            fecha_inicio=fecha_inicio,
            location_filter=location_filter,
            sector_keywords=sector_keywords,
            exclusion_keywords=exclusion_keywords,
            min_cuantia=min_cuantia,
            max_cuantia=max_cuantia
        )
        
        if not candidates:
            return []

        results_aug = []
        for cand in candidates:
            ai_score, explanation, cumple = self._mock_llm_analysis(nit_empresa, cand)
            
            if not cumple:
                continue 

            base_score = cand['score']
            final_score = (base_score * 0.5) + (ai_score * 0.5)
            
            cand['ai_score'] = ai_score
            cand['final_score'] = final_score
            cand['ai_explanation'] = explanation
            results_aug.append(cand)

        results_aug.sort(key=lambda x: x['final_score'], reverse=True)
        return results_aug[:top_k]

    def save_match_run(self, nit_empresa: str, results: List[Dict], filtros: dict = None):
        run = self.match_repo.create_run(MatchRunCreate(
            empresa_nit=nit_empresa,
            filtros_usados=filtros,
            total_encontrados=len(results)
        ))
        
        match_results = []
        for r in results:
            match_results.append(MatchResultModel(
                run_id=run.run_id,
                licitacion_id=r['licitacion_id'],
                score_similitud=r.get('final_score', r['score']),
                estado_revision='pendiente'
            ))
        
        self.match_repo.add_results(match_results)
        self.session.commit()
        return run
