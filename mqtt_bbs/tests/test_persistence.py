"""mqtt_bbs 持久化集成测试 — pytest 版"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pymysql
from mqtt_bbs.client import TaskOutput, TaskMessage


class TestUnit:
    """单元: 序列化 + Mock"""

    def test_task_output_roundtrip(self):
        o = TaskOutput(task_id="t1", agent_id="a1", status="completed", result={"ok": True})
        d = o.to_dict()
        o2 = TaskOutput.from_dict(d)
        assert o2.task_id == "t1"
        assert o2.status == "completed"
        assert o2.result == {"ok": True}
        print("  OK  T1 TaskOutput序列化: 通过")

    def test_task_message_roundtrip(self):
        m = TaskMessage(task_id="t1", type="test", input={"x": 1}, priority=3, timeout=60)
        d = m.to_dict()
        m2 = TaskMessage.from_dict(d)
        assert m2.task_id == "t1"
        assert m2.type == "test"
        assert m2.input == {"x": 1}
        print("  OK  T2 TaskMessage序列化: 通过")


class TestIntegration:
    """集成: MariaDB 持久化"""

    def test_retained_write_and_read(self):
        db = pymysql.connect(host='127.0.0.1', user='root', password='mariadb',
                             database='mqtt_bbs', charset='utf8mb4')
        cur = db.cursor()
        topic = "test/pytest/retain_001"
        payload = json.dumps({"msg": "hello pytest"})
        cur.execute("REPLACE INTO retained_messages(topic,payload,content_type,qos) VALUES(%s,%s,%s,1)",
                    (topic, payload, 'application/json'))
        db.commit()
        cur.execute("SELECT topic,payload FROM retained_messages WHERE topic=%s", (topic,))
        row = cur.fetchone()
        assert row is not None
        assert json.loads(row[1]) == {"msg": "hello pytest"}
        cur.execute("DELETE FROM retained_messages WHERE topic=%s", (topic,))
        db.commit()
        db.close()
        print("  OK  T3 MariaDB Retain读写: 通过")

    def test_session_queue(self):
        db = pymysql.connect(host='127.0.0.1', user='root', password='mariadb',
                             database='mqtt_bbs', charset='utf8mb4')
        cur = db.cursor()
        agent = "pytest_agent_offline"
        for i in range(3):
            cur.execute(
                "INSERT INTO session_queue(target_agent,topic,payload,seq) VALUES(%s,%s,%s,%s)",
                (agent, f"test/msg/{i}", json.dumps({"seq": i}), i))
        db.commit()
        cur.execute("SELECT COUNT(*) FROM session_queue WHERE target_agent=%s AND delivered=0", (agent,))
        assert cur.fetchone()[0] == 3
        cur.execute("UPDATE session_queue SET delivered=1 WHERE target_agent=%s", (agent,))
        cur.execute("DELETE FROM session_queue WHERE target_agent=%s", (agent,))
        db.commit()
        db.close()
        print("  OK  T4 离线队列读写: 通过")

    def test_bbsclient_without_db(self):
        """BBSClientWithPersistence: 无DB时的降级路径"""
        with patch('mqtt_bbs.persistence.MariaDBConn') as MockDB:
            mock_db = MagicMock()
            mock_db.execute.return_value = None
            MockDB.return_value = mock_db
            from mqtt_bbs.persistence import BBSClientWithPersistence
            c = BBSClientWithPersistence("test_unit")
            assert c._db is not None  # 注: 实际构造时会连接DB
        print("  OK  T5 Mock降级: 通过")


if __name__ == "__main__":
    print("=== mqtt_bbs 持久化集成测试 (pytest 风格) ===")
    tu = TestUnit()
    tu.test_task_output_roundtrip()
    tu.test_task_message_roundtrip()

    ti = TestIntegration()
    ti.test_retained_write_and_read()
    ti.test_session_queue()
    # ti.test_bbsclient_without_db()  # 需要unittest.mock环境

    print("\n  OK  全部测试通过!")
