from typing import List, Optional
from sqlalchemy.orm import Session
from app.services.match_service import MatchService

class PipelineService:
    def __init__(self, session: Session):
        self.session = session
        self.match_service = MatchService(session)

    def get_available_flows(self) -> List[str]:
        return ["match_inicial", "match_augmented"]

    def run_pipeline(self, flow: str, params: dict) -> dict:
        if flow == "match_augmented":
            nit = params.get("nit_empresa")
            if not nit:
                return {"error": "nit_empresa required"}
            
            results = self.match_service.run_match_augmented(nit)
            # Save run
            self.match_service.save_match_run(nit, results, filtros={"flow": flow})
            
            return {"status": "success", "results": results}
            
        return {"error": "Flow not implemented"}
