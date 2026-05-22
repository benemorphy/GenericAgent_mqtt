/// Rust WorkerAgent — 任务执行者 (替代 Python bbs.py WorkerAgent)
///
/// 订阅任务 input → 认领 → 执行 → 输出 + 信号 → 完成
use crate::models::BbsRequest;
use crate::client::bbs_client::BBSClient;
use serde_json::Value;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;
use std::sync::Arc;
use tokio::sync::Mutex;
use uuid::Uuid;
use std::collections::HashSet;

const V2_TASK_TOPIC: &str = "v2/task";

pub struct WorkerAgent {
    pub agent_id: String,
    pub client: Arc<BBSClient>,
    capabilities: Vec<String>,
    current_task: Arc<Mutex<Option<String>>>,
    seq: AtomicU64,
    subscribed_dynamic: Arc<Mutex<HashSet<String>>>,
}

impl WorkerAgent {
    pub fn new(agent_id: &str, client: BBSClient, capabilities: Vec<String>) -> Self {
        Self {
            agent_id: agent_id.to_string(),
            client: Arc::new(client),
            capabilities,
            current_task: Arc::new(Mutex::new(None)),
            seq: AtomicU64::new(0),
            subscribed_dynamic: Arc::new(Mutex::new(HashSet::new())),
        }
    }

    pub async fn start(&self) {
        // 发布在线状态
        self.client.publish(
            &format!("agent/node/{}/status", self.agent_id),
            &serde_json::json!("online"),
        ).await;

        // 订阅任务输入 (board + v2 双订阅)
        self.client.subscribe("agent/board/task/+/input", {
            let agent_id = self.agent_id.clone();
            move |topic, payload| {
                let agent_id = agent_id.clone();
                tokio::spawn(async move {
                    // parse task_id from topic
                    // TODO: implement task handling
                });
            }
        }).await;

        // 订阅定向任务
        self.client.subscribe(
            &format!("agent/node/{}/task/input", self.agent_id),
            |topic, payload| {},
        ).await;

        // 订阅全局信号
        self.client.subscribe("agent/board/global/signal", |topic, payload| {}).await;

        tracing::info!("[WorkerAgent] {} 已启动 (capabilities={:?})", self.agent_id, self.capabilities);
    }

    pub async fn claim_task(&self, task_id: &str) -> bool {
        let topic = format!("agent/board/task/{}/claim", task_id);
        let payload = serde_json::json!({
            "agent_id": self.agent_id,
            "claimed_at": chrono::Utc::now().to_rfc3339(),
        });
        self.client.publish(&topic, &payload).await;

        // 更新状态
        let topic_status = format!("agent/board/task/{}/status", task_id);
        self.client.publish(&topic_status, &serde_json::json!("running")).await;

        let topic_busy = format!("agent/node/{}/status", self.agent_id);
        self.client.publish(&topic_busy, &serde_json::json!("busy")).await;

        *self.current_task.lock().await = Some(task_id.to_string());
        tracing::info!("[WorkerAgent] {} 认领任务: {}", self.agent_id, task_id);
        true
    }

    pub async fn stream_out(&self, task_id: &str, text: &str) {
        let seq = self.seq.fetch_add(1, Ordering::SeqCst);
        let topic = format!("agent/board/task/{}/stdout", task_id);
        self.client.publish(&topic, &serde_json::json!({"seq": seq, "data": text})).await;
    }

    pub async fn complete(&self, task_id: &str, status: &str, output: &Value) {
        // 写输出
        let out_topic = format!("agent/board/task/{}/output", task_id);
        let output_msg = serde_json::json!({
            "task_id": task_id, "agent_id": self.agent_id,
            "status": status, "data": output,
            "completed_at": chrono::Utc::now().to_rfc3339(),
        });
        self.client.publish(&out_topic, &output_msg).await;

        // 发送完成信号
        let sig_topic = format!("agent/board/task/{}/signal", task_id);
        self.client.publish(&sig_topic, &serde_json::json!("[ROUND_END]")).await;

        // 更新状态
        let task_status = if status == "completed" { "done" } else { "failed" };
        let st_topic = format!("agent/board/task/{}/status", task_id);
        self.client.publish(&st_topic, &serde_json::json!(task_status)).await;

        // 清理动态订阅
        self.unsubscribe_dynamic().await;

        // 清理自身状态
        let busy_topic = format!("agent/node/{}/status", self.agent_id);
        self.client.publish(&busy_topic, &serde_json::json!("online")).await;

        *self.current_task.lock().await = None;
        tracing::info!("[WorkerAgent] {} 完成任务: {} ({})", self.agent_id, task_id, status);
    }

    async fn unsubscribe_dynamic(&self) {
        let mut subs = self.subscribed_dynamic.lock().await;
        for topic in subs.iter() {
            self.client.unsubscribe(topic);
        }
        subs.clear();
    }
}
