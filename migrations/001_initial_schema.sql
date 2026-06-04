-- Crucible Initial Schema
-- Domain-agnostic. No finance words in the core.

CREATE TABLE IF NOT EXISTS candidates (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    adapter       VARCHAR(100) NOT NULL,
    dna           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    status        VARCHAR(20)  NOT NULL DEFAULT 'EMBRYO',
    budget        FLOAT        NOT NULL DEFAULT 0.0,
    spawn_reason  TEXT,
    retire_reason TEXT,
    born_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    retired_at    TIMESTAMPTZ,
    CONSTRAINT candidate_status CHECK (status IN
        ('EMBRYO','PROVING','PROVEN','DEGRADED','RETIRED','DORMANT'))
);

CREATE TABLE IF NOT EXISTS outcomes (
    id            SERIAL PRIMARY KEY,
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id),
    action        JSONB   NOT NULL DEFAULT '{}'::jsonb,
    result_value  FLOAT   NOT NULL,
    cost          FLOAT   NOT NULL DEFAULT 0.0,
    context       JSONB   NOT NULL DEFAULT '{}'::jsonb,
    is_sealed     BOOLEAN NOT NULL DEFAULT FALSE,
    ts            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verdicts (
    id             SERIAL PRIMARY KEY,
    candidate_id   INTEGER NOT NULL REFERENCES candidates(id),
    verdict        VARCHAR(20) NOT NULL,
    confidence     FLOAT NOT NULL,
    stats          JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence_count INTEGER NOT NULL,
    evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT verdict_check CHECK (verdict IN
        ('UNPROVEN','PROVEN','REJECTED','DEGRADED'))
);

CREATE TABLE IF NOT EXISTS memory (
    id            SERIAL PRIMARY KEY,
    dna_signature VARCHAR(200) NOT NULL,
    adapter       VARCHAR(100) NOT NULL,
    what_worked   TEXT,
    what_failed   TEXT,
    final_stats   JSONB NOT NULL DEFAULT '{}'::jsonb,
    sample_size   INTEGER NOT NULL,
    confidence    FLOAT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS allocations (
    id            SERIAL PRIMARY KEY,
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id),
    budget        FLOAT NOT NULL,
    period        VARCHAR(50),
    rationale     TEXT,
    ts            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_outcomes_candidate ON outcomes(candidate_id);
CREATE INDEX IF NOT EXISTS idx_outcomes_sealed ON outcomes(candidate_id, is_sealed);
CREATE INDEX IF NOT EXISTS idx_verdicts_candidate ON verdicts(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
