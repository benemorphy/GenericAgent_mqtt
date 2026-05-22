use std::sync::Arc;
use rumqttc::{AsyncClient, Event, Incoming, Packet, QoS};
use crate::AppState;
use crate::handlers;

/// 心跳发布循环
pub async fn heartbeat_loop(state: Arc<AppState>) {
    let mut interval = tokio::time::interval(std::time::Duration::from_secs(30));
    loop {
        interval.tick().await;
        let topic = format!("node/{}/heartbeat", state.config.agent_id);
        let payload = serde_json::json!({"ts": chrono::Utc::now().timestamp()});
        if let Err(e) = state.mqtt_client.publish(
            &topic, QoS::AtMostOnce, false,
            serde_json::to_vec(&payload).unwrap(),
        ).await {
            tracing::warn!("心跳发布失败: {}", e);
        }
    }
}

/// MQTT 事件循环 — 主题分发
pub async fn event_loop(state: Arc<AppState>, mut event_loop: rumqttc::EventLoop) -> anyhow::Result<()> {
    loop {
        match event_loop.poll().await {
            Ok(Event::Incoming(Incoming::Publish(publish))) => {
                let topic = publish.topic.clone();
                let payload = publish.payload.to_vec();
                let topic_str = topic.as_str();
                
                // 按主题模式分发 (Python BBSClient 使用 agent/ 前缀)
                if topic_str.starts_with("agent/bbs/") {
                    handle_bbs_topic(&state, topic_str, &payload).await;
                } else if topic_str.starts_with("node/") {
                    handle_node_topic(&state, topic_str, &payload).await;
                } else if topic_str == "board/capability/query" {
                    handlers::capability::handle_cap_query(&state, &payload).await;
                }
            }
            Ok(Event::Incoming(Incoming::ConnAck(_))) => {
                tracing::info!("MQTT 连接成功");
            }
            Ok(Event::Outgoing(_)) => {}
            Err(e) => {
                tracing::warn!("MQTT 事件循环错误: {}", e);
                tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            }
            _ => {}
        }
    }
}

/// 分发 bbs/ 主题
async fn handle_bbs_topic(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    // agent/bbs/{board}/{operation}
    let parts: Vec<&str> = topic.split('/').collect();
    if parts.len() < 4 { return; }
    
    let operation = parts[3];
    match operation {
        "register" => handlers::register::handle_register(state, topic, payload).await,
        "post" => handlers::post::handle_post(state, topic, payload).await,
        "query" => handlers::query::handle_query(state, topic, payload).await,
        "file_init" => handlers::file::handle_file_init(state, topic, payload).await,
        "file_chunk" => handlers::file::handle_file_chunk(state, topic, payload).await,
        "file_commit" => handlers::file::handle_file_commit(state, topic, payload).await,
        "file_download" => handlers::file::handle_file_download(state, topic, payload).await,
        "webhook" | "webhook/config" => handlers::webhook::handle_webhook_config(state, topic, payload).await,
        _ => tracing::debug!("未知 bbs 操作: {}", operation),
    }
}

/// 分发 node/ 主题
async fn handle_node_topic(state: &Arc<AppState>, topic: &str, payload: &[u8]) {
    // node/{agent_id}/{type}
    let parts: Vec<&str> = topic.split('/').collect();
    if parts.len() < 3 { return; }
    
    let msg_type = parts[2];
    match msg_type {
        "status" => handlers::capability::handle_status(state, topic, payload).await,
        "heartbeat" => handlers::capability::handle_heartbeat(state, topic, payload).await,
        "capability" => handlers::capability::handle_capability(state, topic, payload).await,
        _ => tracing::debug!("未知 node 消息类型: {}", msg_type),
    }
}

/// 发布 MQTT 响应 (reply_to 优先, 向后兼容)
pub async fn publish_response(
    client: &AsyncClient,
    reply_to: Option<&str>,
    board_key: &str,
    resp_type: &str,
    corr_id: &str,
    payload: &serde_json::Value,
) {
    let topic = if let Some(rt) = reply_to {
        if corr_id.is_empty() {
            rt.to_string()
        } else {
            format!("{}{}", rt, corr_id)
        }
    } else {
        if corr_id.is_empty() {
            tracing::warn!("响应无 reply_to 也无 corr_id, 丢弃");
            return;
        }
        format!("agent/bbs/{}/{}/{}", board_key, resp_type, corr_id)
    };
    
    let bytes = serde_json::to_vec(payload).unwrap();
    tracing::info!("准备发布响应: topic={}, payload={:?}", topic, payload);
    match client.publish(&topic, QoS::AtLeastOnce, false, bytes).await {
        Ok(()) => tracing::info!("响应发布成功: {}", topic),
        Err(e) => tracing::error!("MQTT 发布失败 [{}]: {}", topic, e),
    }
    tokio::time::sleep(std::time::Duration::from_millis(50)).await;
}
