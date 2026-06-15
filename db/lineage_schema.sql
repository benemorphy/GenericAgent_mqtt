-- GA Lineage DAG + Version 数据库 schema (P4)
-- 用于记录全链路执行轨迹和资源版本管理

CREATE TABLE IF NOT EXISTS lineage (
    id TEXT PRIMARY KEY,
    turn_id TEXT NOT NULL,
    parent_id TEXT,
    agent TEXT,
    action TEXT NOT NULL,
    context TEXT,
    result TEXT,
    status TEXT DEFAULT 'success',
    duration_ms REAL,
    created_at REAL DEFAULT (julianday('now'))
);
CREATE INDEX IF NOT EXISTS idx_lineage_turn ON lineage(turn_id);
CREATE INDEX IF NOT EXISTS idx_lineage_parent ON lineage(parent_id);

CREATE TABLE IF NOT EXISTS resource_versions (
    id TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    version INT NOT NULL,
    stage TEXT DEFAULT 'dev',
    snapshot TEXT NOT NULL,
    checksum TEXT,
    parent_version INT,
    created_by TEXT,
    created_at REAL DEFAULT (julianday('now')),
    UNIQUE(resource_type, resource_id, version)
);
CREATE INDEX IF NOT EXISTS idx_resource_type_id ON resource_versions(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_stage ON resource_versions(stage);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    turn_id TEXT,
    action_type TEXT NOT NULL,
    target TEXT,
    detail TEXT,
    created_at REAL DEFAULT (julianday('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_turn ON audit_log(turn_id);
