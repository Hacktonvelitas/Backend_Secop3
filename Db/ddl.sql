/*
============================================================================
PROYECTO: SISTEMA INTEGRAL DE LICITACIONES (MERGED ARCHITECTURE - FINAL)
DESCRIPCIÓN: Esquema completo unificado (Ingesta, Core, Financiero, RRHH, IT).
============================================================================
*/

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

CREATE TABLE IF NOT EXISTS empresa (
    nit                  VARCHAR(20) PRIMARY KEY,
    razon_social         VARCHAR(255) NOT NULL,
    sigla                VARCHAR(50),
    
    -- Ubicación y Contacto
    pais                 VARCHAR(50) DEFAULT 'Colombia',
    departamento         VARCHAR(100),
    municipio            VARCHAR(100),
    direccion_legal      TEXT,
    correo_contacto      TEXT,
    
    -- Perfil Legal y Tamaño
    fecha_constitucion   DATE,
    anios_existencia     INT,
    tamano_empresarial   VARCHAR(20),
    es_mipyme_acreditada BOOLEAN DEFAULT FALSE,
    
    -- Incentivos de Ley
    tiene_sello_mujer        BOOLEAN DEFAULT FALSE,
    tiene_pers_discapacidad  BOOLEAN DEFAULT FALSE,
    es_zomac                 BOOLEAN DEFAULT FALSE,
    
    -- IA Profile
    razon_social_vec     vector(1536)
);

-- 4.1 HISTÓRICO FINANCIERO
CREATE TABLE IF NOT EXISTS empresa_financieros (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    ano_fiscal          INT NOT NULL,
    
    -- Balance
    activo_corriente    NUMERIC(18, 2),
    activo_total        NUMERIC(18, 2),
    pasivo_corriente    NUMERIC(18, 2),
    pasivo_total        NUMERIC(18, 2),
    patrimonio_neto     NUMERIC(18, 2),
    
    -- Resultados
    utilidad_neta       NUMERIC(18, 2),
    
    -- Capacidad RUP
    k_contratacion_max  NUMERIC(18, 2),
    
    -- Indicadores (Calculados)
    ind_liquidez        NUMERIC(10, 2) GENERATED ALWAYS AS (activo_corriente / NULLIF(pasivo_corriente,0)) STORED,
    ind_endeudamiento   NUMERIC(10, 2) GENERATED ALWAYS AS (pasivo_total / NULLIF(activo_total,0)) STORED,
    
    UNIQUE(empresa_nit, ano_fiscal)
);

-- 4.2 EXPERIENCIA (CONTRATOS EJECUTADOS) + TECH TAGS
CREATE TABLE IF NOT EXISTS empresa_experiencia (
    id                    BIGSERIAL PRIMARY KEY,
    empresa_nit           VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    numero_contrato       VARCHAR(100),
    cliente_nombre        VARCHAR(255),
    sector_cliente        VARCHAR(50), -- 'PUBLICO', 'PRIVADO'
    objeto_contrato       TEXT,
    valor_ejecutado_pesos NUMERIC(18, 2),
    fecha_inicio          DATE,
    fecha_fin             DATE,
    codigos_unspsc        TEXT[], 
    
    -- Nueva columna agregada: Etiquetado Tech
    tech_stack_tags       TEXT[], -- Ej: ['AWS', 'Lambda', 'PostgreSQL']
    
    es_certificado        BOOLEAN DEFAULT TRUE,
    
    -- Vectorización
    objeto_embedding      vector(1536)
);
CREATE INDEX IF NOT EXISTS idx_exp_vec ON empresa_experiencia USING hnsw (objeto_embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_experiencia_tags ON empresa_experiencia USING GIN (tech_stack_tags);

-- 4.3 PARTNERSHIPS Y CERTIFICACIONES DE FABRICANTE (NUEVA TABLA)
CREATE TABLE IF NOT EXISTS empresa_partnerships (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    fabricante          VARCHAR(100), -- Ej: 'Microsoft', 'Oracle'
    nivel_partner       VARCHAR(100), -- Ej: 'Gold', 'Platinum'
    id_partner_global   VARCHAR(100), 
    fecha_vencimiento   DATE,
    certificado_url     TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 4.4 ACTIVOS DE TI / INFRAESTRUCTURA (NUEVA TABLA)
CREATE TABLE IF NOT EXISTS empresa_activos_ti (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    tipo_activo         VARCHAR(50), -- 'SERVIDOR', 'LICENCIA_SOFTWARE'
    nombre_activo       VARCHAR(255), 
    especificaciones    JSONB,       -- { "ram": "64GB", "cores": 16 }
    cantidad_propia     INT DEFAULT 1,
    es_arrendado        BOOLEAN DEFAULT FALSE,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- 4.5 CAPITAL HUMANO (RRHH) + SKILLS AVANZADOS
CREATE TABLE IF NOT EXISTS empresa_equipo (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    nombre_completo     VARCHAR(255),
    titulo_academico    VARCHAR(255),
    nivel_estudio       VARCHAR(50),
    anos_experiencia    NUMERIC(4, 1),
    resumen_perfil      TEXT,
    
    -- Nuevas columnas agregadas
    senior_level        VARCHAR(20), -- 'JUNIOR', 'MID', 'SENIOR'
    idiomas             JSONB,       -- { "ingles": "B2" }
    
    cv_embedding        vector(1536),
    disponible          BOOLEAN DEFAULT TRUE
);

-- 4.6 SKILLS TÉCNICOS ESPECÍFICOS (NUEVA TABLA)
CREATE TABLE IF NOT EXISTS equipo_tech_skills (
    equipo_id           BIGINT REFERENCES empresa_equipo(id) ON DELETE CASCADE,
    tecnologia          VARCHAR(100), -- 'Java', 'Docker'
    anos_experiencia    NUMERIC(3, 1),
    nivel_dominio       INT CHECK (nivel_dominio BETWEEN 1 AND 5),
    PRIMARY KEY (equipo_id, tecnologia)
);

CREATE TABLE IF NOT EXISTS equipo_certificaciones (
    id                  BIGSERIAL PRIMARY KEY,
    equipo_id           BIGINT REFERENCES empresa_equipo(id) ON DELETE CASCADE,
    nombre_cert         VARCHAR(255),
    fecha_vencimiento   DATE
);

-- 4.7 RIESGOS Y SANCIONES
CREATE TABLE IF NOT EXISTS empresa_sanciones (
    id                  BIGSERIAL PRIMARY KEY,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit) ON DELETE CASCADE,
    tipo_sancion        VARCHAR(100), 
    entidad_sancionadora VARCHAR(255),
    fecha_fin           DATE,
    estado_actual       VARCHAR(50)
);

-- =========================================================================
-- 5. MOTOR DE CONSORCIOS (SIMULADOR)
-- =========================================================================

CREATE TABLE IF NOT EXISTS simulacion_consorcios (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nombre_alianza      VARCHAR(255),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    
    liquidez_combinada  NUMERIC(10, 2),
    patrimonio_total    NUMERIC(18, 2),
    k_contratacion_total NUMERIC(18, 2)
);

CREATE TABLE IF NOT EXISTS consorcio_miembros (
    consorcio_id        UUID REFERENCES simulacion_consorcios(id) ON DELETE CASCADE,
    empresa_nit         VARCHAR(20) REFERENCES empresa(nit),
    porcentaje_part     NUMERIC(5, 2),
    PRIMARY KEY (consorcio_id, empresa_nit)
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
    rol                 VARCHAR(50) DEFAULT 'user',
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