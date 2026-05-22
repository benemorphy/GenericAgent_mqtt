use std::sync::Arc;
use crate::{AppState, models::BbsRequest};
use crate::mqtt_handler::publish_response;
use crate::db;

pub async fn handle_register(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let (board_key, req) = match parse_register(topic, payload) {
        Some(v) => v,
        None => return,
    };
    
    let token = uuid::Uuid::new_v4().to_string()[..16].to_string();
    let name = req.name.as_deref().unwrap_or("anonymous");
    
    if let Err(e) = db::upsert_user(&state.db_pool, &board_key, name, &token).await {
        tracing::error!("注册 DB 错误: {}", e);
        return;
    }
    
    let reply_to = req.reply_to.as_deref();
    let corr_id = req.corr_id.as_deref().unwrap_or("");
    
    let resp = serde_json::json!({"token": token, "name": name});
    publish_response(&state.mqtt_client, reply_to, &board_key, "register/response", corr_id, &resp).await;
    
    tracing::info!("注册: {} → token={} (board: {})", name, &token[..8], board_key);
}

fn parse_register(topic: &str, payload: &[u8]) -> Option<(String, BbsRequest)> {
    let parts: Vec<&str> = topic.split('/').collect();
    if parts.len() < 4 { return None; }
    let board_key = parts[2].to_string();
    
    let req: BbsRequest = serde_json::from_slice(payload).ok()?;
    if req.name.as_deref().unwrap_or("").is_empty() {
        return None;
    }
    Some((board_key, req))
}
