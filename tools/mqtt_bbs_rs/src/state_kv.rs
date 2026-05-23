/// StateKV — MariaDB KV 存储
///
/// 对标 Python persistence.py 中的 retained_messages / agent_sessions 管理。
/// 使用 sqlx::MySqlPool 实现简单的 Key-Value 持久化。
use sqlx::MySqlPool;

#[derive(Debug, Clone)]
pub struct StateKV {
    pool: MySqlPool,
}

impl StateKV {
    /// 创建新的 StateKV 实例
    pub fn new(pool: MySqlPool) -> Self {
        Self { pool }
    }

    /// 获取 key 对应的 value
    pub async fn get(&self, key: &str) -> Result<Option<String>, sqlx::Error> {
        let row: Option<(String,)> = sqlx::query_as(
            "SELECT value FROM state_kv WHERE `key` = ?"
        )
        .bind(key)
        .fetch_optional(&self.pool)
        .await?;
        Ok(row.map(|r| r.0))
    }

    /// 设置 key-value（UPSERT）
    pub async fn set(&self, key: &str, value: &str) -> Result<(), sqlx::Error> {
        sqlx::query(
            "INSERT INTO state_kv (`key`, `value`, created_at, updated_at) VALUES (?, ?, NOW(3), NOW(3)) \
             ON DUPLICATE KEY UPDATE `value` = VALUES(`value`), updated_at = NOW(3)"
        )
        .bind(key)
        .bind(value)
        .execute(&self.pool)
        .await?;
        Ok(())
    }

    /// 删除 key
    pub async fn delete(&self, key: &str) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM state_kv WHERE `key` = ?")
            .bind(key)
            .execute(&self.pool)
            .await?;
        Ok(())
    }

    /// 列出所有 keys
    pub async fn keys(&self) -> Result<Vec<String>, sqlx::Error> {
        let rows: Vec<(String,)> = sqlx::query_as("SELECT `key` FROM state_kv ORDER BY `key`")
            .fetch_all(&self.pool)
            .await?;
        Ok(rows.into_iter().map(|r| r.0).collect())
    }
}
