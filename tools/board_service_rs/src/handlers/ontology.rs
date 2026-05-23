/// Ontology Handler — agent/ontology/{id}/{type} 主题空间
///
/// Agent 发布三层本体信息：
///   agent/ontology/{agent_id}/identity    (Who)  — 类型/版本/能力
///   agent/ontology/{agent_id}/knowledge   (What) — 技能/SOP/领域知识
///   agent/ontology/{agent_id}/relations   (How)  — 依赖/对等/协作
///
/// BoardService 存储到 CapabilityRegistry 并提供查询：
///   board/ontology/query → 返回匹配的 Agent 列表
use std::sync::Arc;
use crate::AppState;
use crate::capability::AgentInfo;
use crate::mqtt_handler::publish_response;

/// 处理本体发布
pub async fn handle_identity(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let (agent_id, data) = match parse_ontology(topic, payload) {
        Some(v) => v,
        None => return,
    };
    let caps = data.get("capabilities").and_then(|c| c.as_array())
        .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default();
    let mut info = AgentInfo {
        agent_id: agent_id.clone(),
        capabilities: caps,
        status: "online".to_string(),
        last_seen: chrono::Utc::now().timestamp(),
        load: data.get("load").and_then(|v| v.as_f64()).unwrap_or(0.0),
    };
    // 更新能力注册表
    state.capabilities.write().await.insert(agent_id.clone(), info);
    // 响应
    if let Some(corr_id) = data.get("corr_id").and_then(|c| c.as_str()) {
        let reply_to = format!("agent/ontology/{}/identity/response", agent_id);
        publish_response(&state.mqtt_client, Some(&reply_to), "", "identity", corr_id,
            &serde_json::json!({"ok": true})).await;
    }
}

/// 处理本体查询
pub async fn handle_ontology_query(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    let filter: serde_json::Value = serde_json::from_slice(payload).unwrap_or_default();
    let corr_id = filter.get("corr_id").and_then(|c| c.as_str()).unwrap_or("");
    let cap_filter = filter.get("capability").and_then(|c| c.as_str());

    let agents = state.capabilities.read().await;
    let matched: Vec<&AgentInfo> = agents.values()
        .filter(|a| {
            cap_filter.map_or(true, |f| a.capabilities.iter().any(|c| c == f))
        })
        .collect();

    publish_response(&state.mqtt_client, None, "", "ontology/query", corr_id,
        &serde_json::json!({"agents": matched, "count": matched.len()})).await;
}

fn parse_ontology(topic: &str, payload: &[u8]) -> Option<(String, serde_json::Value)> {
    let parts: Vec<&str> = topic.split('/').collect();
    if parts.len() < 4 { return None; }
    let agent_id = parts[2].to_string();
    let data: serde_json::Value = serde_json::from_slice(payload).ok()?;
    Some((agent_id, data))
}
