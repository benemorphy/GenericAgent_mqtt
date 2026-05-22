/// Rust BoardClient — BBS 协议客户端 (代替 Python board_client.py)
use crate::models::BbsRequest;
use crate::client::bbs_client::BBSClient;

pub struct BoardClient {
    pub agent_id: String,
    pub board: String,
    pub client: BBSClient,
    reply_to: String,
}

impl BoardClient {
    pub async fn new(agent_id: &str, board: &str, host: &str, port: u16) -> Self {
        let c = BBSClient::new(agent_id, host, port).await;
        Self {
            agent_id: agent_id.to_string(),
         
...[Truncated]...
nd(Duration::from_secs(timeout)).await {
            Ok(Some(v)) => Some(v),
            _ => None
        }
    }

    pub async fn register(&self, name: &str, timeout: u64) -> Option<serde_json::Value> {
        let corr_id = uuid::Uuid::new_v4().to_string()[..8].to_string();
        let payload = serde_json::json!({
            "agent_id": self.agent_id, "name": name,
            "corr_id": corr_id, "reply_to": self.reply_to,
        });
        self.client.publish(&format!("agent/bbs/{}/register", self.board), &payload).await;
        self.wait_response(&corr_id, timeout).await
    }
}
