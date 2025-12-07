
-- 1. EXTENSIONES
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- 2. ZONA DE STAGING (INGESTA CRUDA)
-- =========================================================================

CREATE TABLE IF NOT EXISTS staging_licitations (
    lic_id              TEXT PRIMARY KEY,
    chunk_count         BIGINT,
    document_count      BIGINT,
    first_created_at    TIMESTAMPTZ,
    last_created_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS staging_documents (
    doc_id              BIGSERIAL PRIMARY KEY,
    lic_id              TEXT,
    source_name         TEXT,
    source_ext          TEXT,
    sha256              TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging_chunks (
    chunk_id            TEXT PRIMARY KEY,
    lic_id              TEXT,
    doc_id              BIGINT REFERENCES staging_documents(doc_id),
    text_content        TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =========================================================================
-- 3. NÚCLEO LICITACIONES (PUBLIC TENDERS)
-- =========================================================================

CREATE TABLE IF NOT EXISTS public_licitacion (
    id                  SERIAL PRIMARY KEY,
    codigo_proceso      VARCHAR(255) UNIQUE, -- ID único del SECOP/Plataforma
    
    -- Información General
    entidad             VARCHAR(255) NOT NULL,
    objeto              TEXT,
    descripcion_general TEXT,
    modalidad           VARCHAR(255),
    tipo_seleccion      VARCHAR(255),
    fundamento_legal    TEXT,
    ubicacion           VARCHAR(255),
    enlace              TEXT,
    estado              VARCHAR(100),
    
    -- Presupuesto y Valores
    cuantia             NUMERIC(18,2),
    valor_estimado_iva  NUMERIC(18,2),
    presupuesto_ms_oficial NUMERIC(18,2),
    presupuesto_dc_oficial NUMERIC(18,2),
    
    -- Fechas Críticas
    fecha_public        DATE,
    fecha_visita_obra   TIMESTAMPTZ,
    fecha_cierre_oferta TIMESTAMPTZ,
    fecha_adjudicacion_prog DATE,
    plazo_meses         INT,
    
    -- Clasificación
    codigos_unspsc      TEXT[],
    act_econ            VARCHAR(255),

    -- Requisitos Habilitantes (Flags rápidos)
    req_cert_9001       BOOLEAN DEFAULT FALSE,
    req_cert_27001      BOOLEAN DEFAULT FALSE,
    
    -- IA
    objeto_vec          vector(1536) 
);

-- Indices Licitaciones
CREATE INDEX IF NOT EXISTS idx_lic_entidad ON public_licitacion(entidad);
CREATE INDEX IF NOT EXISTS idx_lic_cierre ON public_licitacion(fecha_cierre_oferta);

-- 3.1 DETALLE DE CRITERIOS
CREATE TABLE IF NOT EXISTS licitacion_criterios (
    id                  BIGSERIAL PRIMARY KEY,
    licitacion_id       INT REFERENCES public_licitacion(id) ON DELETE CASCADE,
    nombre_criterio     VARCHAR(255),
    tipo_criterio       VARCHAR(50),  -- 'PUNTAJE', 'HABILITANTE'
    puntaje_maximo      INT,
    descripcion_regla   TEXT,
    embedding_regla     vector(1536)
);

-- 3.2 OBSERVACIONES Y CAMBIOS
CREATE TABLE IF NOT EXISTS licitacion_observaciones (
    id                  BIGSERIAL PRIMARY KEY,
    licitacion_id       INT REFERENCES public_licitacion(id) ON DELETE CASCADE,
    fecha_observacion   TIMESTAMPTZ,
    texto_pregunta      TEXT,
    texto_respuesta     TEXT,
    cambio_requisito    BOOLEAN DEFAULT FALSE,
    embedding_contexto  vector(1536)
);

-- 3.3 GESTIÓN DOCUMENTAL (RAG)
CREATE TABLE IF NOT EXISTS licitacion_documentos (
    id                  BIGSERIAL PRIMARY KEY,
    licitacion_id       INT REFERENCES public_licitacion(id) ON DELETE CASCADE,
    nombre_archivo      VARCHAR(255),
    tipo_contenido      VARCHAR(50),  -- 'PLIEGO', 'ANEXO_TECNICO', 'PRESUPUESTO'
    url_archivo         TEXT,
    procesado_ia        BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public_licitacion_chunk (
    id                  BIGSERIAL PRIMARY KEY,
    documento_id        BIGINT REFERENCES licitacion_documentos(id) ON DELETE CASCADE,
    licitacion_id       INT NOT NULL REFERENCES public_licitacion(id),
    chunk_idx           INT NOT NULL,
    chunk_text          TEXT,
    embedding_vec       vector(1536),
    metadatos_json      JSONB
);

-- =========================================================================
-- 4. NÚCLEO EMPRESARIAL (PERFIL 360 + IT SPECIALIZATION)
-- =========================================================================

CREATE TABLE IF NOT EXISTS empresa_info (
    nit                  VARCHAR(20) PRIMARY KEY,
    razon_social         VARCHAR(255) NOT NULL,
    -- CIIUs
    ciiu1                 VARCHAR(255)
    ciiu2                 VARCHAR(255)
    ciiu3                 VARCHAR(255)
    ciiu4                 VARCHAR(255)
    
    -- Ubicación y Contacto
    pais                 VARCHAR(50) DEFAULT 'Colombia',
    departamento         VARCHAR(100),
    municipio            VARCHAR(100),
    direccion_legal      TEXT,
    correo_contacto      TEXT,
    
    -- Perfil Legal y Tamaño
    fecha_constitucion   DATE,
    anios_existencia     INT,
    tamano_empresarial   VARCHAR(20)
);


CREATE TABLE if NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    razon_social TEXT,
    nit TEXT,
    muncomercial TEXT,
    ciiu1 TEXT,
    ciiu2 TEXT,
    ciiu3 TEXT,
    ciiu4 TEXT,
    razon_social_embedding vector(768),
    ciiu1_embedding vector(768),
    ciiu2_embedding vector(768),
    ciiu3_embedding vector(768),
    ciiu4_embedding vector(768)
);
-- (He quitado la coma que sobraba después de es_zomac o razon_social_vec dependiendo de tu versión anterior)

-- 4.3.1 GESTIÓN DOCUMENTAL DE EMPRESA (S3 + RAG)
-- Esta tabla guarda la referencia al archivo físico en S3
CREATE TABLE IF NOT EXISTS empresa_documentos (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    nombre_archivo      VARCHAR(255), -- Ej: "Camara_Comercio_2025.pdf"
    tipo_documento      VARCHAR(50),  -- 'RUT', 'CAMARA_COMERCIO', 'PORTAFOLIO_SERVICIOS', 'ESTADOS_FINANCIEROS'
    
    -- Conexión con S3
    s3_object_key       TEXT NOT NULL, -- El ID/Path único dentro de tu bucket S3
    s3_bucket_name      VARCHAR(100),  -- Opcional, si usas varios buckets
    url_publica         TEXT,          -- Opcional, si generas URLs firmadas temporalmente
    
    etag_s3             VARCHAR(255),  -- Para verificar integridad o versiones
    procesado_ia        BOOLEAN DEFAULT FALSE,
    uploaded_at         TIMESTAMPTZ DEFAULT NOW()
);


-- =========================================================================
-- 6. USUARIOS Y SISTEMA DE MATCHING
-- =========================================================================

CREATE TABLE IF NOT EXISTS usuario (
    id                  SERIAL PRIMARY KEY,
    email               VARCHAR(255) UNIQUE NOT NULL,
    nombre_completo     VARCHAR(255),
    password_hash       TEXT NOT NULL,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);



-- Log de ejecuciones del algoritmo de matching
CREATE TABLE IF NOT EXISTS match_run (
    run_id              BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit),
    fecha_ejecucion     TIMESTAMPTZ DEFAULT NOW(),
    filtros_usados      JSONB,
    total_encontrados   INT
);

-- Resultados específicos (leads generados)
CREATE TABLE IF NOT EXISTS match_result (
    id                  BIGSERIAL PRIMARY KEY,
    run_id              BIGINT REFERENCES match_run(run_id),
    licitacion_id       INT REFERENCES public_licitacion(id),
    
    score_similitud     FLOAT,
    cluster_asignado    INT,
    
    estado_revision     VARCHAR(50) DEFAULT 'pendiente',
    comentario_usuario  TEXT,
    
    UNIQUE(run_id, licitacion_id)
);