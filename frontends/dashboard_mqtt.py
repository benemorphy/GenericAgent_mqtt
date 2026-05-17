"""
mqtt_bbs Dashboard — MQTT 实时监控面板 (Streamlit)

订阅 MQTT 主题 → 本地缓存 → Streamlit UI 实时展示

用法:
    streamlit run frontends/dashboard_mqtt.py

功能:
    - 集群概览：Agent 总数/在线数、任务总数/各状态
    - Agent 卡片：状态 🟢🟠🔵、能力标签、在线时间
    - 任务列表：类型、状态、输入/输出预览
    - 实时日志：stdout/stderr 尾部追踪
    - 远程干预：取消进行中的任务
    - 自动刷新：可调间隔
"""

import json, logging, os, sys, threading, time
from datetime import datetime

import streamlit as st

# ── 数据源层 ──────────────────────────────────────────

from mqtt_bbs import BBSClient


class MQTTDataSource:
    """MQTT 数据源：订阅所有 task/agent 主题，维护本地缓存"""

    def __init__(self, host="127.0.0.1", port=1883):
        self._lock = threading.Lock()
        self._tasks = {}
        self._agents = {}
        self._agent_logs = {}
        self._client = BBSClient("dashboard_mqtt", host=host)
        self._client.connect()
        self._client.wait_connected(3)
        self._client.subscribe("board/task/+/input", self._on_task_input)
        self._client.subscribe("board/task/+/output", self._on_task_output)
        self._client.subscribe("board/task/+/status", self._on_task_status)
        self._client.subscribe("board/task/+/stdout", self._on_task_stdout)
        self._client.subscribe("board/task/+/stderr", self._on_task_stderr)
        self._client.subscribe("node/+/status", self._on_agent_status)
        self._client.subscribe("node/+/capability", self._on_agent_cap)
        self._client.subscribe("board/task/+/signal", self._on_task_signal)

    def _on_task_input(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            t["task_id"] = task_id
            t["input"] = payload
            t["type"] = payload.get("type", "?") if isinstance(payload, dict) else "?"
            t["status"] = t.get("status", "pending")
            t["updated_at"] = time.time()
            t["created_at"] = t.get("created_at", time.time())

    def _on_task_output(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            t["output"] = payload
            if isinstance(payload, dict):
                if "status" in payload:
                    t["status"] = payload["status"]
                if "result" in payload:
                    t["result"] = payload["result"]
                if "agent" in payload:
                    t["agent"] = payload["agent"]
            t["updated_at"] = time.time()

    def _on_task_status(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        status = (
            payload.get("status", payload)
            if isinstance(payload, dict)
            else (payload.decode() if isinstance(payload, bytes) else str(payload))
        )
        with self._lock:
            self._tasks.setdefault(task_id, {})["status"] = status
            self._tasks[task_id]["updated_at"] = time.time()

    def _on_task_stdout(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            logs = t.setdefault("stdout", [])
            text = payload.get("data", "") if isinstance(payload, dict) else str(payload)
            logs.append(text)
            if len(logs) > 100:
                logs.pop(0)

    def _on_task_stderr(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            errs = t.setdefault("stderr", [])
            text = payload.get("data", "") if isinstance(payload, dict) else str(payload)
            errs.append(text)
            if len(errs) > 100:
                errs.pop(0)

    def _on_agent_status(self, topic, payload):
        parts = topic.split("/")
        agent_id = parts[1] if len(parts) >= 2 else "?"
        status = (
            payload.get("status", payload)
            if isinstance(payload, dict)
            else (payload.decode() if isinstance(payload, bytes) else str(payload))
        )
        with self._lock:
            self._agents.setdefault(agent_id, {})["status"] = status
            self._agents[agent_id]["updated_at"] = time.time()
            if status == "online" and "connected_at" not in self._agents[agent_id]:
                self._agents[agent_id]["connected_at"] = time.time()

    def _on_agent_cap(self, topic, payload):
        parts = topic.split("/")
        agent_id = parts[1] if len(parts) >= 2 else "?"
        with self._lock:
            self._agents.setdefault(agent_id, {})["capabilities"] = payload

    def _on_task_signal(self, topic, payload):
        parts = topic.split("/")
        task_id = parts[2] if len(parts) >= 3 else "?"
        signal = payload.decode() if isinstance(payload, bytes) else str(payload)
        with self._lock:
            t = self._tasks.setdefault(task_id, {})
            t["signal"] = signal
            t["updated_at"] = time.time()

    def get_tasks(self):
        with self._lock:
            return dict(self._tasks)

    def get_agents(self):
        with self._lock:
            return dict(self._agents)

    def cancel_task(self, task_id):
        self._client.publish(f"board/task/{task_id}/signal", "[CANCEL]", retain=True, qos=2)

    def publish_task(self, task_type: str, task_input: dict):
        """发布一个任务到 AgentBoard"""
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        msg = {
            "task_id": task_id,
            "type": task_type,
            "input": task_input,
            "priority": 3,
            "timeout": 300,
            "created_at": datetime.now().isoformat(),
        }
        self._client.publish(f"board/task/{task_id}/input", msg, retain=True, qos=2)
        return task_id

    def close(self):
        self._client.disconnect()


# ── Streamlit UI ──────────────────────────────────────
# 仅在 streamlit run 模式下执行
if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(page_title="MQTT Agent Dashboard", page_icon="🤖", layout="wide")

    st.title("🤖 MQTT Agent Dashboard")
    st.caption("实时监控 MQTT BBS 上的 Agent 集群与任务状态")

    # 侧边栏配置
    with st.sidebar:
        st.header("🔌 连接配置")
        broker_host = st.text_input("Broker 地址", value="127.0.0.1")
        broker_port = st.number_input("Broker 端口", value=1883, min_value=1, max_value=65535)
        refresh_rate = st.slider("刷新间隔 (秒)", min_value=1, max_value=30, value=3)
        st.divider()
        st.header("📤 发布测试任务")
        with st.form("publish_task"):
            task_type = st.text_input("任务类型", value="test_ping")
            task_target = st.text_input("目标", value="localhost")
            col1, col2 = st.columns(2)
            with col1:
                submitted = st.form_submit_button("🚀 发布", use_container_width=True)
            with col2:
                st.caption("任务将发送到 AgentBoard")

    # 初始化数据源
    if "ds" not in st.session_state:
        try:
            ds = MQTTDataSource(host=broker_host, port=broker_port)
            st.session_state.ds = ds
            st.success(f"✅ 已连接到 {broker_host}:{broker_port}")
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")
            st.info("确保 MQTT Broker 在运行: `rmqtt start --daemon`")
            st.stop()

    ds = st.session_state.ds

    # 发布任务
    if submitted:
        with st.spinner("发布中..."):
            task_id = ds.publish_task(task_type, {"target": task_target})
            st.success(f"✅ 任务已发布: {task_id}")

    # 获取数据
    agents = ds.get_agents()
    tasks = ds.get_tasks()

    # ── 集群概览 ──
    st.header("📊 集群概览")
    total_agents = len(agents)
    online_agents = sum(1 for a in agents.values() if a.get("status") == "online")
    total_tasks = len(tasks)
    done_tasks = sum(1 for t in tasks.values() if t.get("status") in ("completed", "done", "success"))
    pending_tasks = sum(1 for t in tasks.values() if t.get("status") in ("pending", "running", "processing"))
    failed_tasks = sum(1 for t in tasks.values() if t.get("status") in ("failed", "error", "timeout"))

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🤖 Agent 总数", total_agents, delta=f"{online_agents} 在线")
    col2.metric("📋 任务总数", total_tasks)
    col3.metric("✅ 已完成", done_tasks)
    col4.metric("⏳ 进行中", pending_tasks)
    col5.metric("❌ 失败", failed_tasks)

    # ── Agent 卡片 ──
    st.header("🃏 Agent 列表")
    if not agents:
        st.info("暂无 Agent 连接")
    else:
        cols = st.columns(3)
        for i, (agent_id, info) in enumerate(sorted(agents.items())):
            with cols[i % 3]:
                status = info.get("status", "unknown")
                status_emoji = {"online": "🟢", "offline": "🔴", "busy": "🟠", "unknown": "⚪"}.get(status, "⚪")
                caps = info.get("capabilities", [])
                if isinstance(caps, str):
                    caps = [caps]
                caps_str = ", ".join(caps[:5]) if caps else "无"
                connected_at = info.get("connected_at")
                online_for = ""
                if connected_at:
                    elapsed = int(time.time() - connected_at)
                    if elapsed < 60:
                        online_for = f"{elapsed}s"
                    elif elapsed < 3600:
                        online_for = f"{elapsed // 60}m"
                    else:
                        online_for = f"{elapsed // 3600}h"

                with st.container(border=True):
                    st.markdown(f"**{status_emoji} {agent_id}** `{status}`")
                    if online_for:
                        st.caption(f"在线时长: {online_for}")
                    st.caption(f"能力: {caps_str}")

    # ── 任务列表 ──
    st.header("📋 任务列表")
    if not tasks:
        st.info("暂无任务")
    else:
        sorted_tasks = sorted(tasks.items(), key=lambda x: x[1].get("created_at", 0), reverse=True)

        for task_id, info in sorted_tasks:
            status = info.get("status", "unknown")
            task_type = info.get("type", "?")
            agent = info.get("agent", "?")
            result = info.get("result", "")
            created = info.get("created_at", 0)
            updated = info.get("updated_at", 0)

            status_color = {
                "completed": "green", "done": "green", "success": "green",
                "pending": "orange", "running": "blue", "processing": "blue",
                "failed": "red", "error": "red", "timeout": "red",
                "cancelled": "gray",
            }.get(status, "gray")

            with st.expander(f"`{task_id[:20]}...` — **{task_type}** — :{status_color}[{status}] — Agent: {agent}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("**输入:**")
                    st.code(json.dumps(info.get("input", {}), indent=2, ensure_ascii=False)[:500])
                    if info.get("result"):
                        st.markdown("**结果:**")
                        res = result
                        st.code(json.dumps(res, indent=2, ensure_ascii=False)[:500] if isinstance(res, dict) else str(res)[:500])
                    # 日志
                    stdout = info.get("stdout", [])
                    stderr = info.get("stderr", [])
                    if stdout or stderr:
                        tab1, tab2 = st.tabs(["📤 stdout", "📥 stderr"])
                        with tab1:
                            st.code("\n".join(stdout[-20:]) if stdout else "无")
                        with tab2:
                            st.code("\n".join(stderr[-20:]) if stderr else "无")

                with col2:
                    if st.button(f"🛑 取消", key=f"cancel_{task_id}", use_container_width=True):
                        ds.cancel_task(task_id)
                        st.toast(f"已发送取消信号: {task_id}")

    # 自动刷新
    time.sleep(0.1)
    st.rerun()
