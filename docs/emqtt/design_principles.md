# emqtt 设计原则与架构分析

> 基于 https://github.com/emqx/emqtt (Erlang MQTT 5.0 Client) 源码分析
> Erlang 97.5% | 15 个源文件 | Apache-2.0

---

## 一、架构总览

```

用户代码/CLI
    │
emqtt:connect/1 → gen_statem 状态机 (emqtt.erl, 2547行)
    │                    │
    ├─ emqtt_frame.erl   ── parse/serialize      (协议层, 788行)
    ├─ emqtt_sock.erl     ── gen_tcp / ssl       (传输层, 194行)
    ├─ emqtt_ws.erl       ── gun WebSocket       (传输层)
    ├─ emqtt_inflight.erl ── QoS重试/确认队列    (可靠性层)
    ├─ emqtt_props.erl    ── v5 30+属性定义      (元数据层)
    ├─ emqtt_quic.erl     ── QUIC传输            (实验)
    └─ emqtt_cli.erl      ── CLI命令行工具
```

### 设计原则 0: 模块化分离 — 单一职责

| 模块 | 职责 | 关键函数 |
|------|------|----------|
| `emqtt` | 主状态机 (gen_statem) | `connect/4`, `subscribe/3`, `publish/4` |
| `emqtt_frame` | 协议帧编解码 | `parse/2`, `serialize/1` |
| `emqtt_sock` | TCP/TLS 套接字 | `open/3`, `send/2`, `recv/2` |
| `emqtt_ws` | WebSocket 传输 | `open/3`, `close/1` |
| `emqtt_inflight` | 飞行窗口管理 | `new/1`, `insert/3`, `delete/2` |
| `emqtt_props` | MQTT v5 属性 | `serialize_property/2`, `parse_properties/2` |

**原则: 一个模块只做一件事，可独立测试和替换**

---

## 二、协议帧编解码 (emqtt_frame.erl)

### 设计原则 1: 二进制模式匹配 — 零开销协议解码

```erlang
%% MQTT固定头一行解析 (Type/Dup/QoS/Retain 共1字节):
parse(<<Type:4, Dup:1, QoS:2, Retain:1, Rest/binary>>,
      #{strict_mode := StrictMode, version := Ver}) ->
    Header = #mqtt_packet_header{type=Type, dup=bool(Dup),
                                 qos=QoS, retain=bool(Retain)},
    parse_remaining_len(Rest, Header, Options).

%% CONNECT报文逐位解包:
<<UsernameFlag:1, PasswordFlag:1, WillRetain:1,
  WillQoS:2, WillFlag:1, CleanStart:1,
  0:1, KeepAlive:16/big, Rest2/binary>> = Rest1
```

**优势**: Erlang 的位级模式匹配直接映射到 MQTT 协议规范，无需逐字节解析。
**零开销**: 编译为高效的二进制匹配指令，无中间对象。

### 设计原则 2: Continuation — TCP 流式增量解析

```erlang
%% 数据不完整时 → 返回 continuation function
parse_remaining_len(<<>>, Header, Options) ->
    {more, fun(Bin) -> parse_remaining_len(Bin, Header, Options) end};

%% 解析完成 → 返回 {ok, Packet, Rest}
parse_remaining_len(Rest, Header, Options) ->
    parse_remaining_len(Rest, Header, 1, 0, Options).

%% 使用示例:
{ok, Packet, _Rest} = emqtt_frame:parse(Binary, Options).
```

**Continuation 链**:
```
parse/2 → parse_remaining_len/5 → parse_frame/4 → parse_packet/3
                                                         ↓
                                              {ok, Packet, Rest}
                                              {more, Continuation} ← 不完整时
```

**流式处理**: `Transport` 层每次收到数据都尝试解析，不完整时保存 continuation。

### 设计原则 3: 函数式状态机 — 无副作用

```erlang
%% 每个解析函数只依赖参数，无 mutable state:
parse(Bin, Options)          → {ok, Packet, Rest} | {more, Fun} | {error, Reason}
parse_remaining_len(_, _, _) → ...
parse_frame(Header, Len, O)  → ...
parse_packet(Header, Bin, O) → ...
```

每个阶段都是纯函数，输出仅决定于输入，适合**管道风格**编程。

---

## 三、属性系统 (emqtt_props.erl)

### 设计原则 4: 编译期模式匹配 → MQTT v5 属性编码

```erlang
%% 每种属性有固定ID码 — 通过模式匹配安全映射:
serialize_property('Session-Expiry-Interval', Val) -> <<16#11, Val:32/big>>;
serialize_property('Payload-Format-Indicator', Val) -> <<16#01, Val:8>>;
serialize_property('Content-Type', Val)            -> <<16#03, (serialize_utf8_string(Val))/binary>>;
serialize_property('User-Property', {Key, Val})     -> <<16#26, (serialize_utf8_string(Key))/binary,
                                                               (serialize_utf8_string(Val))/binary>>;
... 30+ 种属性全覆盖
```

**漏写 → 编译错误**: Erlang 的 `case` / function clause 检查确保所有属性都被处理。

### 设计原则 4a: Iodata — 零拷贝序列化

```erlang
%% 不是构建大二进制，而是返回 iodata 列表:
serialize_properties(Props) ->
    Bin = << <<(serialize_property(P,V))/binary>> || {P,V} <- maps:to_list(Props) >>,
    [serialize_variable_byte_integer(byte_size(Bin)), Bin].
```

**优势**: `gen_tcp:send(Socket, Iodata)` 直接发送底层缓冲区，**无中间拷贝**。

---

## 四、套接字抽象 (emqtt_sock.erl + emqtt_ws.erl)

### 设计原则 5: 传输层多路抽象

```erlang
%% 统一接口，支持多种传输协议:

%% TCP (gen_tcp)
open(Host, Port, #{tcp_opts := TcpOpts}) ->
    gen_tcp:connect(Host, Port, [binary, {packet, raw}, {active, false} | TcpOpts]);

%% TLS (ssl 模块)
open(Host, Port, #{tls_opts := TlsOpts}) ->
    ssl:connect(Host, Port, [binary, {active, false} | TlsOpts]);

%% WebSocket (gun 库)
emqtt_ws:open(Host, Port, WsOpts) ->
    gun:open(Host, Port, #{protocols => [gun_ws]}).

%% QUIC (quicer 库) — 实验性
emqtt_quic:open(Host, Port, QuicOpts).
```

**架构**: 所有传输方式对外暴露 `open/send/recv/close` 统一接口，主状态机不关心底层传输。

---

## 五、飞行队列 (emqtt_inflight.erl)

### 设计原则 6: 泛型键值存储 → QoS 重试

```erlang
%% 核心数据结构: #{seq => PacketIdCounter, queue => #{PktId => Msg}}
new(RetryInterval) -> #{seq => 1, queue => #{}, retry => RetryInterval}.

insert(PktId, Msg, Inflight) ->
    case size(Inflight) < max_inflight() of
        true  -> {ok, Inflight#{PktId => Msg}};
        false -> {error, full}
    end.

delete(PktId, Inflight) ->
    Inflight#{PktId := deleted}.

%% 重试: 遍历所有未确认的消息重新发送
retry(Inflight) ->
    maps:fold(fun(K, V, Acc) when V =/= deleted ->
                  [send(K, V) | Acc];
                 (_, _, Acc) -> Acc
              end, [], Inflight).
```

**设计**: 泛型 `{seq, queue}` 结构，`insert/delete` 原子操作，超时重试逻辑独立。

---

## 六、gen_statem 状态机 (emqtt.erl)

### 设计原则 7: 显示状态转换 → 连接生命周期

```
initialized ──connect({Host,Port,Opts})──→ connecting
     ↑                                          │
     │            connack 收到                    │ state_timeout 100ms
     │            ───────────────                │
     │            connected                      │
     │              │                            │
     │     ┌────────┼────────┐                   │
     │     │        │        │                   │
     │  publish  subscribe  disconnect            │
     │     │        │        │                   │
     │     └────────┴────────┘                   │
     │              │                            │
     │           disconnecting                    │
     │              │                            │
     └──── reconn_timer ──────┘ (自动重连)
```

```erlang
%% state callbacks:
initialized({call, _}, {connect, Host, Port, Opts}, _) ->
    {next_state, connecting, Data#{host=>Host, port=>Port},
     {state_timeout, 100, connack}};

connecting(state_timeout, connack, Data) ->
    %% 超时未收到 CONNACK → 重连
    {next_state, connecting, Data, {state_timeout, 1000, reconnect}};

connected({call, _}, {publish, Topic, Payload, Opts}, Data) ->
    %% 发布消息，记录到 inflight
    {keep_state, Data2, [{reply, {ok, PktId}}]};

connected({call, _}, disconnect, Data) ->
    {stop_and_reply, normal, [{reply, ok}], Data}.
```

**Emqtt 特色**: `state_timeout` + 嵌套数据结构 `Data` 管理所有连接上下文。

---

## 七、数据类型

### 原则 8: Opaque 类型 + 类型规范

```erlang
-type(mqtt_msg() :: #mqtt_msg{}).
-type(packet_id() :: 1..65535).
-type(reconnect() :: infinity | non_neg_integer()).

%% CONNACK 结构化解析:
-record(mqtt_packet_connack, {
    ack_flags    :: non_neg_integer(),
    reason_code  :: byte(),
    properties   :: map()
}).

-opaque(tref() :: reference()).
```

**opaque** 隐藏实现细节，对外只暴露 API 函数。

---

## 八、模块依赖图

```
emqtt_cli ← CLI入口
    │
emqtt ← 主状态机 (gen_statem)
    ├── emqtt_frame    → 协议编解码
    ├── emqtt_props    → v5属性定义
    ├── emqtt_inflight → 飞行队列
    ├── emqtt_sock     → TCP/TLS传输
    ├── emqtt_ws       → WebSocket传输
    └── emqtt_quic     → QUIC传输(实验)
```

---

## 总结: 8 大设计原则

| # | 原则 | 体现 | Erlang 特性 |
|---|------|------|-------------|
| 1 | **二进制模式匹配** | 协议帧逐位解析 | `<<Type:4, Dup:1, ...>>` |
| 2 | **Continuation 增量** | TCP流式解析 | `fun(Bin) -> ... end` closure |
| 3 | **函数式无副作用** | parse链无可变状态 | 纯函数管道 |
| 4 | **编译期安全** | 属性ID模式匹配 | function clause 编译检查 |
| 4a | **Iodata 零拷贝** | 序列化输出 iolist | `gen_tcp:send` 直接引用 |
| 5 | **传输层多路** | TCP/TLS/WS/QUIC统一接口 | behavior-like |
| 6 | **泛型飞行队列** | QoS重试抽象 | map + fold |
| 7 | **显式状态机** | 生命周期驱动 | `gen_statem + state_timeout` |
| 8 | **Opaque 类型** | 隐藏实现细节 | `-opaque()` 编译检查 |
