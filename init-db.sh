#!/bin/sh
set -eu

echo "[init] Esperando a que Postgres inicie..."
# Nota: En los scripts de initdb.d, el socket suele estar listo, 
# pero mantener el check es buena práctica de seguridad.
until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
  sleep 1
done

# Habilitar extensión vector ANTES de restaurar (por si los dumps la usan)
echo "[init] Habilitando extensión vector..."
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# ----------------------------------------------------------------
# RESTAURACIÓN 1: BASE DE DATOS PRINCIPAL
# ----------------------------------------------------------------
if [ -f /docker-entrypoint-initdb.d/backup_main.dump ]; then
  echo "[init] 1. Restaurando backup PRINCIPAL (rag_db)..."
  pg_restore \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean --if-exists \
    --no-owner --no-privileges \
    -j 4 \
    /docker-entrypoint-initdb.d/backup_main.dump || echo "[WARN] Errores no críticos en restore principal"
else
  echo "[init][WARN] No se encontró backup_main.dump"
fi

# ----------------------------------------------------------------
# RESTAURACIÓN 2: COMPANIES
# ----------------------------------------------------------------
if [ -f /docker-entrypoint-initdb.d/backup_companies.dump ]; then
  echo "[init] 2. Restaurando tabla COMPANIES..."
   pg_restore \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner --no-privileges \
    -j 4 \
    /docker-entrypoint-initdb.d/backup_companies.dump || echo "[WARN] Errores no críticos en restore companies"
    
  echo "[init] Restauración de companies finalizada."
else
  echo "[init] No se encontró backup_companies.dump, omitiendo."
fi

echo "[init] Proceso finalizado exitosamente ✅"