import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa

engine = create_engine(os.getenv('DATABASE_URL'))
Session = sessionmaker(bind=engine)
session = Session()

results = obtener_oportunidades_empresa(
    session=session,
    nit_empresa='900123456',
    top_k=5,
    min_score=0.0,
    sector_filter=None,
    exclusion_filter=None,
    location_filter=None,
    rango_cuantia=None,
    fecha_inicio=None,
    n_clusters=1,
)
print('Number of matches:', len(results))
for r in results:
    print(r)
