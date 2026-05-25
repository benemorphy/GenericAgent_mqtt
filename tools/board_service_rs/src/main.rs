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
    db::init_capabilities_table(&db_pool).await?;
    
    // 初始化 MQTT 客户端
    let client_id = format!("{}_{}", config.agent_id, uuid::Uuid::new_v4().to_string().split('-').next().unwrap());
    let mut mqtt_opts = rumqttc::MqttOptions::new(&client_id, &config.broker_host, config.broker_port);
    // MQTT 认证 (P0.2)
    if !config.broker_username.is_empty() {
        mqtt_opts.set_credentials(&config.broker_username, &config.broker_password);
        tracing::info!("MQTT 认证已配置: username={}", config.broker_username);
    }
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
    mqtt_client.subscribe("agent/ontology/#", rumqttc::QoS::AtLeastOnce).await?;
    mqtt_client.subscribe("board/ontology/query", rumqttc::QoS::AtLeastOnce).await?;
    
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
    
    // Plugin IPC watchdog: 子进程死亡自动重启
    if config.plugin_cmd.is_empty() {
        // noop
    } else {
        let wd_state = state.clone();
        let wd_cmd = config.plugin_cmd.clone();
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(std::time::Duration::from_secs(10)).await;
                let plugin_dead = {
                    let ipc = wd_state.plugin_ipc.read().await;
                    ipc.is_none() // 简化：IPC 存在即认为正常，实际需进程 PID 检查
                };
                if plugin_dead {
                    tracing::warn!("Plugin IPC 子进程已死亡，尝试重启...");
                    // 重新 spawn
                    if let Ok(new_ipc) = PluginIpc::spawn(&wd_cmd).await {
                        let mut ipc = wd_state.plugin_ipc.write().await;
                        *ipc = Some(new_ipc);
                        tracing::info!("Plugin IPC 子进程已重启");
                    }
                }
            }
        });
    }
    
    // B0: 启动时收集 retain 能力声明（含DB持久化）
    let cap_db = db_pool.clone();
    tokio::spawn({
        let s = state.clone();
        async move {
            tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            tracing::info!("B0: 启动后等待 retain 消息收集...");
            // retain 消息会在连接后自动推送, 等待 2s 让它们到达
            tokio::time::sleep(std::time::Duration::from_secs(2)).await;
            let count = s.capabilities.read().await.len();
            tracing::info!("B0: 已收集 {} 个 Agent 能力声明", count);
            
            // 从DB加载持久化的能力（补充retain未覆盖的离线但已注册Agent）
            if let Ok(rows) = db::load_capabilities(&cap_db).await {
                let mut caps = s.capabilities.write().await;
                for (agent_id, caps_json, version, status, last_seen, load, ttl) in rows {
                    let capabilities: Vec<String> = serde_json::from_str(&caps_json).unwrap_or_default();
                    caps.entry(agent_id.clone()).or_insert_with(|| {
                        tracing::debug!("B0: 从DB恢复Agent: {}", agent_id);
                        crate::capability::AgentInfo {
                            agent_id,
                            capabilities,
                            version: version as u64,
                            status,
                            last_seen,
                            load,
                            ttl: ttl as u64,
                        }
                    });
                }
                tracing::info!("B0: DB恢复完成, 总Agent: {}", s.capabilities.read().await.len());
            }
        }
    });
    
    // B0: SIGTERM 处理
    let sig_state = state.clone();
    tokio::spawn(async move {
        tokio::signal::ctrl_c().await.expect("信号处理失败");
        tracing::info!("B0: 收到 SIGTERM, 正在关闭...");
        // 发布离线状态
        if let Err(e) = sig_state.mqtt_client.publish(
            &format!("node/{}/status", sig_state.config.agent_id),
            rumqttc::QoS::AtLeastOnce, true, b"offline"
        ).await {
            tracing::warn!("发布离线状态失败: {}", e);
        }
        std::process::exit(0);
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
