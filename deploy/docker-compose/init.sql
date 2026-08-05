-- My Test Project 초기 스키마
-- PostgreSQL 최초 기동 시 자동 실행됩니다.

-- ── Users ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id       UUID PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    display_name  VARCHAR(255),
    role          VARCHAR(20) NOT NULL DEFAULT 'member',
    team_id       UUID,
    github_username VARCHAR(100),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- ── Samples ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS samples (
    sample_id     UUID PRIMARY KEY,
    title         VARCHAR(255) NOT NULL,
    content       TEXT NOT NULL DEFAULT '',
    status        VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_by    UUID NOT NULL REFERENCES users(user_id),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status);
CREATE INDEX IF NOT EXISTS idx_samples_created_by ON samples(created_by);
