use std::sync::Arc;
use crate::AppState;
use crate::capability::AgentInfo;

pub async fn handle_status(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let agent_id = topic.split('/').nth(1).unwrap_or("");
    if agent_id.is_empty() { return; }
    let status = String::from_utf8_lossy(payload).trim().to_string();
    
    let mut caps = state.capabilities.write().await;
    let entry = caps.agents.entry(agent_id.to_string()).or_insert_with(|| AgentInfo {
        agent_id: agent_id.to_string(),
        capabilities: vec![],
        status: "unknown".to_string(),
        last_seen: chrono::Utc::now().timestamp(),
        load: 0.0,
    });
    entry.status = status.clone();
    entry.last_seen = chrono::Utc::now().timestamp();
    tracing::debug!("Agent 状态: {} = {}", agent_id, status);
}

pub async fn handle_heartbeat(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let agent_id = topic.split('/').nth(1).unwrap_or("");
    if agent_id.is_empty() { return; }
    
    let mut caps = state.capabilities.write().await;
    if let Some(entry) = caps.agents.get_mut(agent_id) {
        entry.last_seen = chrono::Utc::now().timestamp();
        entry.status = "online".to_string();
        if let Ok(p) = serde_json::from_slice::<serde_json::Value>(payload) {
            entry.load = p.get("load").and_then(|v| v.as_f64()).unwrap_or(entry.load);
        }
    }
}

pub async fn handle_capability(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let agent_id = topic.split('/').nth(1).unwrap_or("");
    if agent_id.is_empty() { return; }
    
    if let Ok(caps) = serde_json::from_slice::<Vec<String>>(payload) {
        let mut cap_reg = state.capabilities.write().await;
        let entry = cap_reg.agents.entry(agent_id.to_string()).or_insert_with(|| AgentInfo {
            agent_id: agent_id.to_string(),
            capabilities: vec![],
            status: "online".to_string(),
            last_seen: chrono::Utc::now().timestamp(),
            load: 0.0,
        });
        entry.capabilities = caps;
        entry.last_seen = chrono::Utc::now().timestamp();
        tracing::info!("Agent 能力: {} = {:?}", agent_id, entry.capabilities);
    }
}

pub async fn handle_cap_query(state: &Arc<AppState>, payload: &[u8]) {
    let req: serde_json::Value = serde_json::from_slice(payload).unwrap_or_default();
    let corr_id = req.get("corr_id").and_then(|v| v.as_str()).unwrap_or("");
    let filter = req.get("filter").and_then(|v| v.as_str()).unwrap_or("");
    
    let cap_reg = state.capabilities.read().await;
    let agents: Vec<&AgentInfo> = cap_reg.agents.values()
        .filter(|a| a.status != "offline")
        .filter(|a| filter.is_empty() || a.capabilities.iter().any(|c| c.contains(filter)))
        .collect();
    
    let resp = serde_json::json!({
        "type": "capability_list",
        "agents": agents,
        "count": agents.len(),
        "timestamp": chrono::Utc::now().timestamp(),
    });
    
    if !corr_id.is_empty() {
        let topic = format!("board/capability/query/response/{}", corr_id);
        if let Err(e) = state.mqtt_client.publish(&topic, rumqttc::QoS::AtLeastOnce, false,
            serde_json::to_vec(&resp).unwrap()).await {
            tracing::warn!("能力查询响应发布失败: {}", e);
        }
    }
}
