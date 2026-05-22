mod mqtt_handler;
mod models;
mod plugin_ipc;
mod handlers;

mod config;
mod db;
mod capability;
mod app_state;
use std::sync::Arc;
use tokio::sync::RwLock;
use clap::Parser;
use tracing_subscriber::EnvFilter;
use config::Config;
use db::DbPool;
use crate::capability::AgentInfo;
use plugin_ipc::PluginIpc;

/// 共享应用状态
pub struct AppState {
    pub config: Config,
    pub db_pool: DbPool,
    pub mqtt_client: rumqttc::AsyncClient,
    pub capabilities: RwLock<std::collections::HashMap<String, AgentInfo>>,
    pub webhooks: RwLock<std::collections::HashMap<String, Vec<String>>>,
    pub plugin_ipc: RwLock<Option<PluginIpc>>,
}

impl AppState {
    pub fn topic_bbs(&self, suffix: &str) -> String {
        format!("{}/{}", self.config.topic_bbs, suffix)
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let config = Config::parse();
    
    // 初始化日志
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::new(&config.log_level))
        .init();
    
    tracing::info!("BoardService RS 启动 (agent_id={})", config.agent_id);
    
    // 初始化数据库连接池
    let db_pool = db::init_pool(&config.db_url, config.db_pool_size).await?;
    tracing::info!("数据库连接池就绪 ({} connections)", config.db_pool_size);
    
    // 初始化 MQTT 客户端
    let client_id = format!("{}_{}", config.agent_id, uuid::Uuid::new_v4().to_string().split('-').next().unwrap());
    let mqtt_opts = rumqttc::MqttOptions::new(&client_id, &config.broker_host, config.broker_port);
    let (mqtt_client, event_loop) = rumqttc::AsyncClient::new(mqtt_opts, 100);
    
    // 连接并订阅（Python 客户端使用 agent/ 前缀）
    mqtt_client.subscribe("agent/bbs/+/register", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/post", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/query", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/file_init", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/file_chunk", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/file_commit", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/file_download", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("agent/bbs/+/webhook/config", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("node/+/status", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("node/+/heartbeat", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("node/+/capability", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("board/capability/query", rumqttc::QoS::AtLeastOnce).await?;
    
    tracing::info!("MQTT 订阅完成 (broker={}:{})", config.broker_host, config.broker_port);
    
    // 初始化 Plugin IPC
    let plugin_ipc = if config.plugin_cmd.is_empty() {
        None
    } else {
        Some(PluginIpc::spawn(&config.plugin_cmd).await?)
    };
    
    // 构建 AppState
    let state = Arc::new(AppState {
        config: config.clone(),
        db_pool,
        mqtt_client: mqtt_client.clone(),
        capabilities: RwLock::new(std::collections::HashMap::new()),
        webhooks: RwLock::new(std::collections::HashMap::new()),
        plugin_ipc: RwLock::new(plugin_ipc),
    });
    
    // 启动心跳发布
    let hb_state = state.clone();
    tokio::spawn(async move {
        mqtt_handler::heartbeat_loop(hb_state).await;
    });
    
    // 事件循环
    tracing::info!("BoardService RS 启动完成，等待消息...");
    mqtt_handler::event_loop(state, event_loop).await?;
    
    Ok(())
}
