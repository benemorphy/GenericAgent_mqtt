"""
MQTT 客户端注册脚本（带 JWT 认证）
用法:
  1. 先用邮箱和密码登录获取 JWT token
  2. 用 JWT token 向 BoardService 注册 MQTT 客户端

步骤:
  python scripts/mqtt_client_register_jwt.py <email> <password> <board_key>
  
示例:
  python scripts/mqtt_client_register_jwt.py benemorphy@126.com Test123456 test_board
"""

import sys, json, time, argparse
import requests as req
import paho.mqtt.client as mqtt

# ── 配置 ──
GATEWAY_URL = "http://localhost:8001"
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_TEMPLATE = "bbs/{board_key}/register"

def login_get_jwt(email: str, password: str) -> str:
    """通过 Gateway 邮箱登录获取 JWT"""
    resp = req.post(
        f"{GATEWAY_URL}/api/email/login",
        data={"email": email, "password": password},
        allow_redirects=False,
    )
    # JWT 在 Set-Cookie 头中
    cookie = resp.headers.get("set-cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("token="):
            return part[len("token="):]
    raise RuntimeError(f"登录失败: {resp.status_code}, cookie={cookie}, body={resp.text[:200]}")


def register_via_mqtt(board_key: str, jwt_token: str) -> dict:
    """通过 MQTT 向 BoardService 注册客户端，等待响应"""
    topic = TOPIC_TEMPLATE.format(board_key=board_key)
    reply_topic = f"bbs/{board_key}/register/response/{time.time_ns()}"

    result = {"token": None, "jwt": None}

    def on_connect(client, userdata, flags, rc, reason=None):
        if rc == 0:
            print(f"[MQTT] 已连接 (rc={rc})")
            client.subscribe(reply_topic, qos=1)
            # 发送注册请求
            payload = json.dumps({
                "name": board_key,
                "token": jwt_token,
                "reply_to": reply_topic,
                "corr_id": "register-jwt-test",
            })
            client.publish(topic, payload, qos=1)
            print(f"[MQTT] 注册请求已发送 -> {topic}")
        else:
            print(f"[MQTT] 连接失败: rc={rc}")

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            result["token"] = data.get("token")
            result["jwt"] = data.get("jwt")
            print(f"[MQTT] 注册响应: token={data.get('token','N/A')[:16]}...")
            client.disconnect()
        except json.JSONDecodeError as e:
            print(f"[MQTT] 响应解析失败: {e}, payload={msg.payload[:200]}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"register-jwt-{time.time_ns()}")
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    # 等待 5 秒
    wait_until = time.time() + 5.0
    while time.time() < wait_until and result["token"] is None:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MQTT 客户端注册（带 JWT）")
    parser.add_argument("email", help="邮箱地址")
    parser.add_argument("password", help="密码")
    parser.add_argument("board_key", help="板块键值")
    args = parser.parse_args()

    try:
        print(f"[1/2] 登录获取 JWT: {args.email}")
        jwt = login_get_jwt(args.email, args.password)
        print(f"[OK] JWT 获取成功: {jwt[:30]}...")

        print(f"[2/2] MQTT 注册到板块: {args.board_key}")
        result = register_via_mqtt(args.board_key, jwt)
        if result["token"]:
            print(f"[OK] 注册成功! token={result['token']}")
            print(f"[OK] BoardService JWT={result['jwt'][:30]}...")
        else:
            print("[FAIL] 注册超时或失败")
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
