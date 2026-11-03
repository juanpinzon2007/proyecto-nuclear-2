-- EXPERIMENTAL. Delta exacto de BD2_03_AUTORIZACION_U1.md, sin triggers.
BEGIN;
ALTER TABLE caso
  ADD COLUMN uuid_caso UUID,
  ADD COLUMN uuid_version UUID,
  ADD COLUMN numero_version INTEGER,
  ADD COLUMN contenido_congelado BOOLEAN,
  ADD CONSTRAINT uq_er28_caso_uuid_version UNIQUE (uuid_version),
  ADD CONSTRAINT uq_er28_caso_familia_numero UNIQUE (uuid_caso, numero_version),
  ADD CONSTRAINT ck_er28_caso_referencia_completa CHECK (
    (uuid_caso IS NULL AND uuid_version IS NULL AND numero_version IS NULL
      AND contenido_congelado IS NULL)
    OR
    (uuid_caso IS NOT NULL AND uuid_version IS NOT NULL AND numero_version IS NOT NULL
      AND numero_version > 0 AND contenido_congelado IS NOT NULL)
  );
ALTER TABLE rubrica
  ADD COLUMN uuid_publico UUID,
  ADD COLUMN version_regla VARCHAR(20),
  ADD CONSTRAINT uq_er28_rubrica_uuid_publico UNIQUE (uuid_publico),
  ADD CONSTRAINT ck_er28_rubrica_referencia_completa CHECK (
    (uuid_publico IS NULL AND version_regla IS NULL)
    OR
    (uuid_publico IS NOT NULL AND version_regla IS NOT NULL
      AND length(btrim(version_regla)) > 0)
  );
COMMIT;
