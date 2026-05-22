use sqlx::mysql::{MySqlPool, MySqlPoolOptions};
use mqtt_bbs_rs::models::{Post, UserRow, FileSession};

pub type DbPool = MySqlPool;

/// 初始化连接池
pub async fn init_pool(db_url: &str, max_connections: u32) -> anyhow::Result<DbPool> {
    let pool = MySqlPoolOptions::new()
        .max_connections(max_connections)
        .connect(db_url)
        .await?;
    Ok(pool)
}

// ── 注册 ──

pub async fn upsert_user(pool: &DbPool, board: &str, name: &str, token: &str) -> anyhow::Result<()> {
    sqlx::query(
        "INSERT INTO bbs_users (token, name, board) VALUES (?, ?, ?)
         ON DUPLICATE KEY UPDATE token = VALUES(token), name = VALUES(name)"
    )
    .bind(token).bind(name).bind(board)
    .execute(pool).await?;
    Ok(())
}

pub async fn find_user_by_token(pool: &DbPool, token: &str) -> anyhow::Result<Option<UserRow>> {
    let row = sqlx::query_as::<_, UserRow>("SELECT token, name, board FROM bbs_users WHERE token = ?")
        .bind(token)
        .fetch_optional(pool).await?;
    Ok(row)
}

// ── 帖子 ──

pub async fn insert_post(pool: &DbPool, board: &str, author: &str, content: &str) -> anyhow::Result<i64> {
    let result = sqlx::query(
        "INSERT INTO bbs_posts (board, author, content, created_at) VALUES (?, ?, ?, NOW(3))"
    )
    .bind(board).bind(author).bind(content)
    .execute(pool).await?;
    Ok(result.last_insert_id() as i64)
}

pub async fn query_posts(
    pool: &DbPool, board: &str, author: Option<&str>,
    limit: i64, offset: i64,
) -> anyhow::Result<Vec<Post>> {
    if let Some(a) = author {
        let rows = sqlx::query_as::<_, Post>(
            "SELECT id, board, author, content, created_at FROM bbs_posts
             WHERE board = ? AND author = ? ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        .bind(board).bind(a).bind(limit).bind(offset)
        .fetch_all(pool).await?;
        Ok(rows)
    } else {
        let rows = sqlx::query_as::<_, Post>(
            "SELECT id, board, author, content, created_at FROM bbs_posts
             WHERE board = ? ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        .bind(board).bind(limit).bind(offset)
        .fetch_all(pool).await?;
        Ok(rows)
    }
}

pub async fn count_posts(pool: &DbPool, board: &str, author: Option<&str>) -> anyhow::Result<i64> {
    if let Some(a) = author {
        let row: (i64,) = sqlx::query_as(
            "SELECT COUNT(*) FROM bbs_posts WHERE board = ? AND author = ?"
        )
        .bind(board).bind(a)
        .fetch_one(pool).await?;
        Ok(row.0)
    } else {
        let row: (i64,) = sqlx::query_as(
            "SELECT COUNT(*) FROM bbs_posts WHERE board = ?"
        )
        .bind(board)
        .fetch_one(pool).await?;
        Ok(row.0)
    }
}

pub async fn list_authors(pool: &DbPool, board: &str) -> anyhow::Result<Vec<String>> {
    let rows: Vec<(String,)> = sqlx::query_as(
        "SELECT DISTINCT author FROM bbs_posts WHERE board = ? ORDER BY author"
    )
    .bind(board)
    .fetch_all(pool).await?;
    Ok(rows.into_iter().map(|r| r.0).collect())
}

// ── 文件会话 (分片上传) ──

pub async fn create_file_session(
    pool: &DbPool, session_id: &str, board_key: &str,
    filename: &str, total_size: i64, chunk_count: i32, uploader: &str,
) -> anyhow::Result<()> {
    sqlx::query(
        "INSERT INTO file_sessions (session_id, board_key, filename, total_size, chunk_count, received_chunks, status, uploader)
         VALUES (?, ?, ?, ?, ?, 0, 'init', ?)"
    )
    .bind(session_id).bind(board_key).bind(filename)
    .bind(total_size).bind(chunk_count).bind(uploader)
    .execute(pool).await?;
    Ok(())
}

pub async fn insert_file_chunk(
    pool: &DbPool, session_id: &str, seq: i32, data: &[u8],
) -> anyhow::Result<()> {
    sqlx::query(
        "INSERT INTO file_chunks (session_id, seq, data) VALUES (?, ?, ?)"
    )
    .bind(session_id).bind(seq).bind(data)
    .execute(pool).await?;
    
    sqlx::query(
        "UPDATE file_sessions SET received_chunks = received_chunks + 1 WHERE session_id = ?"
    )
    .bind(session_id)
    .execute(pool).await?;
    Ok(())
}

pub async fn get_file_chunks(
    pool: &DbPool, session_id: &str,
) -> anyhow::Result<Vec<(i32, Vec<u8>)>> {
    let rows: Vec<(i32, Vec<u8>)> = sqlx::query_as(
        "SELECT seq, data FROM file_chunks WHERE session_id = ? ORDER BY seq"
    )
    .bind(session_id)
    .fetch_all(pool).await?;
    Ok(rows)
}

pub async fn get_file_session(pool: &DbPool, session_id: &str) -> anyhow::Result<Option<FileSession>> {
    let row = sqlx::query_as::<_, FileSession>(
        "SELECT session_id, board_key, filename, total_size, chunk_count, received_chunks,
                status, uploader, created_at
         FROM file_sessions WHERE session_id = ?"
    )
    .bind(session_id)
    .fetch_optional(pool).await?;
    Ok(row)
}

pub async fn complete_file_session(pool: &DbPool, session_id: &str) -> anyhow::Result<()> {
    sqlx::query("UPDATE file_sessions SET status = 'completed' WHERE session_id = ?")
        .bind(session_id).execute(pool).await?;
    Ok(())
}

pub async fn cleanup_file_chunks(pool: &DbPool, session_id: &str) -> anyhow::Result<()> {
    sqlx::query("DELETE FROM file_chunks WHERE session_id = ?")
        .bind(session_id).execute(pool).await?;
    Ok(())
}
