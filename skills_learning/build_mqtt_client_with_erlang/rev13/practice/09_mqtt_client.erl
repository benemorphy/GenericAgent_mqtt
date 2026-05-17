%%%===================================================================
%%% Exercise 9: MQTT 真实连接 — 连接公共 Broker
%%% 演示: 用 gen_tcp 连接 broker.emqx.io (1883)
%%%       发送 CONNECT → 接收 CONNACK → 发布 → 断开
%%% 编译: erlc 09_mqtt_client.erl
%%% 运行: erl -noshell -s 09_mqtt_client test -s init stop
%%%===================================================================
-module('09_mqtt_client').
-export([test/0, parse_remaining_len/2]).

test() ->
    io:format("=== MQTT 真实连接测试 ===~n~n"),
    Host = "broker.emqx.io",
    Port = 1883,
    ClientId = <<"erlang_mqtt_demo_", (integer_to_binary(erlang:system_time(millisecond)))/binary>>,

    io:format("1. 连接 ~s:~p~n", [Host, Port]),
    {ok, Sock} = gen_tcp:connect(Host, Port, [binary, {active, false}, {packet, raw}], 5000),
    io:format("   TCP 连接成功!~n"),

    io:format("2. 发送 CONNECT 报文~n"),
    ProtoVer = 5,  Flags = 2,  KeepAlive = 30,
    VarHeader = <<0,4,77,81,84,84, ProtoVer, Flags, KeepAlive:16/big>>,
    Payload = <<(byte_size(ClientId)):16/big, ClientId/binary>>,
    RemLen = byte_size(VarHeader) + byte_size(Payload),
    ok = gen_tcp:send(Sock, <<16, RemLen, VarHeader/binary, Payload/binary>>),
    io:format("   已发送 CONNECT~n"),

    io:format("3. 接收 CONNACK~n"),
    {ok, Resp} = gen_tcp:recv(Sock, 0, 5000),
    io:format("   原始响应 (~p bytes): ~p~n", [byte_size(Resp), Resp]),
    <<_Type, Rest/binary>> = Resp,
    {_RemLen, <<_AckFlags, Code, _/binary>>} = parse_remaining_len(Rest, 0),
    case Code of
        0 -> io:format("   ✅ CONNACK accepted!~n");
        C -> io:format("   ❌ CONNACK refused: Code=~p (~ts)~n", [C, reason(Code)])
    end,

    io:format("4. 发布消息~n"),
    Topic = <<"test/erlang">>,  Msg = <<"Hello from Erlang OTP 28!">>,
    Pkt = <<48, (2 + byte_size(Topic) + byte_size(Msg)),
            (byte_size(Topic)):16/big, Topic/binary, Msg/binary>>,
    ok = gen_tcp:send(Sock, Pkt),
    io:format("   已发布到 test/erlang~n"),

    io:format("5. 断开~n"),
    ok = gen_tcp:send(Sock, <<224, 0>>),
    timer:sleep(100), gen_tcp:close(Sock),
    io:format("~n=== OK! broker.emqx.io 连通正常 ===~n").

%% 可变长度整数解析 (MQTT 剩余长度)
parse_remaining_len(<<1:1, V:7, R/binary>>, A) -> parse_remaining_len(R, A+V);
parse_remaining_len(<<0:1, V:7, R/binary>>, A) -> {A+V, R}.

%% MQTT v5 原因码翻译
reason(0) -> <<"Success">>;
reason(1) -> <<"Unspecified error">>;
reason(5) -> <<"Not authorized">>;
reason(135) -> <<"Server busy">>;
reason(151) -> <<"Receive maximum exceeded">>;
reason(157) -> <<"Connection rate exceeded">>;
reason(_) -> <<"Unknown">>.
