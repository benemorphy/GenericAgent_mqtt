// mqtt_bbs_rs — MQTT BBS Rust 客户端库
// Stage 2: 可复用的客户端组件

pub mod client;      // BBSClient (MQTT封装)
pub mod models;      // 数据模型 (共享)
pub mod db;          // MariaDB 查询 (共享)

// 仅二进制需要的模块
#[cfg(feature = "server")]
pub mod config;
#[cfg(feature = "server")]
pub mod mqtt_handler;
#[cfg(feature = "server")]
pub mod handlers;
#[cfg(feature = "server")]
pub mod capability;
#[cfg(feature = "server")]
pub mod plugin_ipc;

// 客户端功能 (Stage 2)
pub mod state_kv;
pub mod file_transfer;
