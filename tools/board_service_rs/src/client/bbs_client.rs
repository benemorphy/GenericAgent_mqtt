/// Rust BBSClient — MQTT 客户端封装 (代替 Python client.py)
use rumqttc::{AsyncClient, MqttOptions, QoS, Event, Incoming, Packet};
use tokio::sync::mpsc;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

type Callback = Arc<dyn Fn(String, serde_json::Value) + Send + Sync>;

pub struct BBSClient {
    client: AsyncClient,
    callbacks: Arc<Mutex<HashMap<String, Vec<Callback>>>>,
    connected: Arc<Mutex<bool>>,
    #[allow(dead_code)]
    rx: mpsc::Receiver<()>,
}

impl BBSClient {
    pub async fn 
...[Truncated]...
        let bytes = serde_json::to_vec(&payload).unwrap_or_default();
        self.client.publish(&topic, QoS::AtLeastOnce, false, bytes).await.ok();
    }

    pub async fn subscribe<F>(&self, pattern: &str, callback: F)
    where F: Fn(String, serde_json::Value) + Send + Sync + 'static
    {
        let mut cb = self.callbacks.lock().await;
        cb.entry(pattern.to_string()).or_default().push(Arc::new(callback));
        self.client.subscribe(pattern, QoS::AtLeastOnce).await.ok();
    }
}
