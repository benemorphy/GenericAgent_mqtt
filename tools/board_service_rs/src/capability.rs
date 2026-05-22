use std::collections::HashMap;
use serde::Serialize;

/// Agent 信息
#[derive(Debug, Clone, Serialize)]
pub struct AgentInfo {
    pub agent_id: String,
    pub capabilities: Vec<String>,
    pub status: String,
    pub last_seen: i64,
    pub load: f64,
}

/// CapabilityRegistry — 去中心化 Agent 能力注册表
pub struct CapabilityRegistry {
    pub agents: HashMap<String, AgentInfo>,
}

impl CapabilityRegistry {
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }
}
