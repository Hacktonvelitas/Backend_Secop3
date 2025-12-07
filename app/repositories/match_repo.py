from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.match import MatchRun, MatchResult
from app.schemas.match import MatchRunCreate

class MatchRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, run_in: MatchRunCreate) -> MatchRun:
        db_obj = MatchRun(**run_in.model_dump())
        self.session.add(db_obj)
        self.session.flush()
        return db_obj

    def add_results(self, results: List[MatchResult]):
        self.session.add_all(results)
        self.session.flush()

    def get_run_by_id(self, run_id: int) -> Optional[MatchRun]:
        return self.session.get(MatchRun, run_id)
