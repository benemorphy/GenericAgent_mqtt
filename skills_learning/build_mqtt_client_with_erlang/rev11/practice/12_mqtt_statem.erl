%%%===================================================================
%%% Exercise 12: MQTT 客户端状态机 — 基于 emqtt.erl 的 gen_statem
%%% 演示: Erlang gen_statem 行为管理 MQTT 连接生命周期
%%% 原理: emqtt.erl (2547行) 的核心状态机
%%% 状态: initialized → connecting → connected → disconnecting
%%% 编译: erlc 12_mqtt_statem.erl
%%% 运行: erl -noshell -s 12_mqtt_statem test -s init stop
%%%===================================================================
-module('12_mqtt_statem').
-behaviour(gen_statem).
-export([start_link/0, connect/0, publish/2, subscribe/2, disconnect/0, test/0]).
-export([init/1, callback_mode/0, terminate/3]).
-export([initialized/3, connecting/3, connected/3]).

%% ============ 客户端 API ============
start_link() ->
    gen_statem:start_link({local, mqtt_client}, ?MODULE, [], []).

connect() ->
    gen_statem:call(mqtt_client, connect).

publish(Topic, Payload) ->
    gen_statem:call(mqtt_client, {publish, Topic, Payload}).

subscribe(Topic, QoS) ->
    gen_statem:call(mqtt_client, {subscribe, Topic, QoS}).

disconnect() ->
    gen_statem:call(mqtt_client, disconnect).

%% ============ 回调 ============
init([]) ->
    io:format("   [init] MQTT 客户端启动~n"),
    {ok, initialized, #{}}.

callback_mode() -> state_functions.

%% ============ 状态: initialized ============
initialized({call, From}, connect, Data) ->
    io:format("   [initialized] 收到 connect 命令~n"),
    io:format("   [initialized] → connecting (发送 CONNECT 报文)...~n"),
    %% 模拟发送 CONNECT 报文
    ConnPacket = #{clientid => <<"erlang_statem_demo">>, 
                   keepalive => 30, proto_ver => 5},
    {next_state, connecting, Data#{conn_packet => ConnPacket, 
                                   from => From}, 
     [{state_timeout, 100, connack}]};  %% 模拟等待 CONNACK

initialized(EventType, Content, Data) ->
    io:format("   [initialized] 忽略: ~p ~p~n", [EventType, Content]),
    {keep_state, Data}.

%% ============ 状态: connecting ============
connecting(state_timeout, connack, Data) ->
    io:format("   [connecting] 收到 CONNACK~n"),
    io:format("   [connecting] → connected (连接建立成功)~n"),
    {next_state, connected, Data#{connect_time => erlang:system_time(second)}};

connecting({call, From}, disconnect, Data) ->
    io:format("   [connecting] 收到 disconnect, 停止连接~n"),
    {stop_and_reply, normal, [{reply, From, ok}], Data};

connecting(EventType, Content, Data) ->
    io:format("   [connecting] 忽略: ~p ~p~n", [EventType, Content]),
    {keep_state, Data}.

%% ============ 状态: connected ============
connected({call, From}, {publish, Topic, Payload}, Data) ->
    PacketId = maps:get(next_pktid, Data, 1),
    io:format("   [connected] PUBLISH topic=~ts, payload=~ts, pktId=~p~n", 
              [Topic, Payload, PacketId]),
    {keep_state, Data#{next_pktid => PacketId + 1}, 
     [{reply, From, {ok, PacketId}}]};

connected({call, From}, {subscribe, Topic, QoS}, Data) ->
    PacketId = maps:get(next_pktid, Data, 1),
    io:format("   [connected] SUBSCRIBE topic=~ts, QoS=~p, pktId=~p~n", 
              [Topic, QoS, PacketId]),
    {keep_state, Data#{next_pktid => PacketId + 1}, 
     [{reply, From, {ok, PacketId}}]};

connected({call, From}, disconnect, Data) ->
    io:format("   [connected] 收到 disconnect, 发送 DISCONNECT...~n"),
    io:format("   [connected] → (停止)~n"),
    {stop_and_reply, normal, [{reply, From, ok}], Data};

connected(info, {tcp_closed, _Sock}, Data) ->
    io:format("   [connected] TCP 连接断开, 准备重连...~n"),
    %% emqtt 的连接重连机制: 自动转回 connecting
    {next_state, connecting, Data#{reconnect => true}, 
     [{state_timeout, 1000, reconnect}]};

connected(state_timeout, reconnect, Data) ->
    io:format("   [connecting] 重连中...~n"),
    {next_state, connected, Data};

connected(EventType, Content, Data) ->
    io:format("   [connected] 忽略: ~p ~p~n", [EventType, Content]),
    {keep_state, Data}.

terminate(_Reason, _State, _Data) ->
    io:format("   [terminate] MQTT 客户端停止~n"),
    ok.

%% ============ 测试 ============
test() ->
    io:format("=== MQTT gen_statem 状态机演示 ===~n~n"),
    
    %% 启动状态机
    {ok, _Pid} = start_link(),
    io:format("~n"),
    
    %% 连接
    ok = connect(),
    io:format("~n"),
    
    %% 等待进入 connected 状态
    timer:sleep(200),
    
    %% 发布消息
    {ok, PktId1} = publish(<<"test/topic">>, <<"hello">>),
    io:format("   发布成功: packetId=~p~n", [PktId1]),
    
    %% 订阅
    {ok, PktId2} = subscribe(<<"sensor/#">>, 1),
    io:format("   订阅成功: packetId=~p~n", [PktId2]),
    
    %% 再发一条
    {ok, PktId3} = publish(<<"test/status">>, <<"running">>),
    io:format("   发布成功: packetId=~p~n", [PktId3]),
    io:format("~n"),
    
    %% 断开
    ok = disconnect(),
    
    init:stop().

test_impl() ->
    ok.
