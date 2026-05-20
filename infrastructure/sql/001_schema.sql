-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Patients
CREATE TABLE IF NOT EXISTS patients (
    patient_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fhir_id         VARCHAR(128) UNIQUE NOT NULL,
    mrn             VARCHAR(64),
    first_name      VARCHAR(128),
    last_name       VARCHAR(128),
    date_of_birth   DATE,
    gender          VARCHAR(16),
    hospital_id     VARCHAR(64),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Observations (vitals + labs)
CREATE TABLE IF NOT EXISTS observations (
    obs_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    fhir_obs_id     VARCHAR(128),
    category        VARCHAR(64),
    code            VARCHAR(64),
    feature_name    VARCHAR(128),
    display         VARCHAR(256),
    value_quantity  FLOAT,
    unit            VARCHAR(32),
    reference_low   FLOAT,
    reference_high  FLOAT,
    is_abnormal     BOOLEAN DEFAULT FALSE,
    status          VARCHAR(32),
    effective_at    TIMESTAMPTZ,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Medications
CREATE TABLE IF NOT EXISTS medications (
    med_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    fhir_med_id     VARCHAR(128),
    medication_name VARCHAR(256),
    rxnorm_code     VARCHAR(64),
    dosage          VARCHAR(128),
    route           VARCHAR(64),
    status          VARCHAR(32),
    start_date      TIMESTAMPTZ,
    end_date        TIMESTAMPTZ,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Conditions (diagnoses)
CREATE TABLE IF NOT EXISTS conditions (
    cond_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    fhir_cond_id    VARCHAR(128),
    code            VARCHAR(64),
    display         VARCHAR(256),
    severity        VARCHAR(32),
    onset_date      TIMESTAMPTZ,
    abatement_date  TIMESTAMPTZ,
    clinical_status VARCHAR(32),
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Causal graphs (per patient, versioned)
CREATE TABLE IF NOT EXISTS causal_graphs (
    graph_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    version         INTEGER NOT NULL DEFAULT 1,
    adjacency_json  JSONB NOT NULL DEFAULT '[]',
    effect_sizes    JSONB NOT NULL DEFAULT '{}',
    node_list       JSONB NOT NULL DEFAULT '[]',
    samples_used    INTEGER,
    build_time_ms   FLOAT,
    is_current      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- AI recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    rec_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(patient_id),
    doctor_id       VARCHAR(128),
    rec_type        VARCHAR(64),
    intervention    VARCHAR(256),
    causal_effect   FLOAT,
    confidence_low  FLOAT,
    confidence_high FLOAT,
    evidence_json   JSONB,
    zk_proof_hash   VARCHAR(256),
    doctor_action   VARCHAR(64),
    outcome         VARCHAR(64),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(64),
    entity_type     VARCHAR(64),
    entity_id       VARCHAR(128),
    actor_id        VARCHAR(128),
    actor_role      VARCHAR(32),
    details_json    JSONB,
    zk_proof_hash   VARCHAR(256),
    occurred_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_obs_patient
    ON observations(patient_id, effective_at DESC);
CREATE INDEX IF NOT EXISTS idx_obs_feature
    ON observations(patient_id, feature_name);
CREATE INDEX IF NOT EXISTS idx_med_patient
    ON medications(patient_id, status);
CREATE INDEX IF NOT EXISTS idx_cond_patient
    ON conditions(patient_id, clinical_status);
CREATE INDEX IF NOT EXISTS idx_graph_current
    ON causal_graphs(patient_id, is_current);
CREATE INDEX IF NOT EXISTS idx_rec_patient
    ON recommendations(patient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity
    ON audit_log(entity_type, entity_id, occurred_at DESC);
