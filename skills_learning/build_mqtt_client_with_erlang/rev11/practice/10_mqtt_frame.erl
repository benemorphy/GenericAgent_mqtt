%%%===================================================================
%%% Exercise 10: MQTT Frame Parser — 基于 emqtt_frame 的设计模式
%%% 演示: Erlang 二进制模式匹配解析 MQTT 协议帧
%%% 原理: emqtt_frame:parse/2 使用 continuation 增量解析
%%% 编译: erlc 10_mqtt_frame.erl
%%% 运行: erl -noshell -s 10_mqtt_frame test -s init stop
%%%===================================================================
-module('10_mqtt_frame').
-export([parse_header/1, parse_remaining_len/1, parse_connect/1, 
         serialize_connect/1, test/0]).

%% MQTT 报文类型常量
-define(CONNECT,     1).
-define(CONNACK,     2).
-define(PUBLISH,     3).
-define(PUBACK,      4).
-define(SUBSCRIBE,   8).
-define(SUBACK,      9).
-define(PINGREQ,     12).
-define(PINGRESP,    13).
-define(DISCONNECT,  14).

%% ============ 解析部分 ============

%% 解析 MQTT 固定头: <<Type:4, Dup:1, QoS:2, Retain:1>>
parse_header(<<Type:4, Dup:1, QoS:2, Retain:1, Rest/binary>>) ->
    Header = #{type => Type, dup => Dup, qos => QoS, retain => Retain},
    {Header, Rest}.

%% 解析剩余长度 (Variable Byte Integer)
%% MQTT 规范: 每个字节最高位表示是否继续
parse_remaining_len(Bin) ->
    parse_remaining_len(Bin, 0, 1).

parse_remaining_len(<<0:1, Len:7, Rest/binary>>, Acc, Multiplier) ->
    {Acc + Len * Multiplier, Rest};
parse_remaining_len(<<1:1, Len:7, Rest/binary>>, Acc, Multiplier) ->
    parse_remaining_len(Rest, Acc + Len * Multiplier, Multiplier * 128);
parse_remaining_len(<<>>, _Acc, _Multiplier) ->
    {more, need_more_data}.  %% continuation 模式

%% 解析 CONNECT 报文
parse_connect(Bin) ->
    {Header, Rest0} = parse_header(Bin),
    #{type := ?CONNECT} = Header,  %% 断言是 CONNECT
    {RemLen, Rest1} = parse_remaining_len(Rest0),
    <<FrameBody:RemLen/binary, _/binary>> = Rest1,
    
    %% 解析协议名 (UTF-8 字符串)
    <<ProtoLen:16/big, ProtoName:ProtoLen/binary, Rest2/binary>> = FrameBody,
    
    %% 解析协议级别
    <<ProtoVer:8, Rest3/binary>> = Rest2,
    
    %% 解析连接标志 (按位分解)
    <<UserFlag:1, PassFlag:1, WillRetain:1, WillQoS:2, 
      WillFlag:1, CleanStart:1, _Reserved:1, KeepAlive:16/big,
      Rest4/binary>> = Rest3,
    
    %% 解析 Client ID (UTF-8 字符串)
    <<CidLen:16/big, ClientId:CidLen/binary, _/binary>> = Rest4,
    
    {ok, #{proto_name => ProtoName, proto_ver => ProtoVer,
           clean_start => CleanStart, keepalive => KeepAlive,
           clientid => ClientId, will_flag => WillFlag,
           will_qos => WillQoS, will_retain => WillRetain,
           user_flag => UserFlag, pass_flag => PassFlag}}.

%% ============ 序列化部分 ============

%% 序列化 CONNECT 报文 (简化版)
serialize_connect(Opts) ->
    ProtoName = <<0,4, "MQTT">>,
    ProtoVer  = maps:get(proto_ver, Opts, 5),
    ClientId  = maps:get(clientid, Opts, <<"erlang_demo">>),
    KeepAlive = maps:get(keepalive, Opts, 30),
    CleanSt   = maps:get(clean_start, Opts, 1),
    
    %% 可变头 + 载荷
    VariableHeader = <<ProtoName/binary, ProtoVer:8,
                       CleanSt:1, 0:7,  %% 连接标志 (简化)
                       KeepAlive:16/big>>,
    Payload = <<(byte_size(ClientId)):16/big, ClientId/binary>>,
    
    Body = <<VariableHeader/binary, Payload/binary>>,
    RemLen = byte_size(Body),
    
    %% 固定头: 类型=CONNECT, 剩余长度
    FixedHeader = <<?CONNECT:4, 0:1, 0:2, 0:1>>,
    serialize_remaining_len(FixedHeader, RemLen, Body).

%% 序列化剩余长度 (可变字节整数)
serialize_remaining_len(FH, Len, Body) when Len =< 127 ->
    <<FH/binary, 0:1, Len:7, Body/binary>>;
serialize_remaining_len(FH, Len, Body) ->
    Byte = 128 + (Len rem 128),
    serialize_remaining_len(<<FH/binary, Byte:8>>, Len div 128, Body).

%% ============ UTF-8 字符串工具 ============
parse_utf8_string(<<Len:16/big, Str:Len/binary, Rest/binary>>) ->
    {Str, Rest}.

serialize_utf8_string(Str) when is_binary(Str) ->
    <<(byte_size(Str)):16/big, Str/binary>>.

%% ============ 测试 ============
test() ->
    io:format("=== MQTT Frame Parser Demo ===~n~n"),
    
    %% 1) 手动构建 MQTT CONNECT 报文
    ClientId = <<"erlang_frame_demo">>,
    ProtoName = <<0,4,"MQTT">>,
    Payload = <<(byte_size(ClientId)):16/big, ClientId/binary>>,
    Body = <<ProtoName/binary, 5:8,     %% MQTT v5
             0:1,0:1,0:1,0:2,0:1,1:1,0:1,  %% 连接标志: CleanStart=1
             30:16/big,                    %% KeepAlive=30s
             Payload/binary>>,
    RemLen = byte_size(Body),
    Packet = <<?CONNECT:4, 0:1, 0:2, 0:1,   %% 固定头
               RemLen:8,                     %% 剩余长度
               Body/binary>>,
    
    io:format("1. 手动构建 CONNECT 报文:~n   ~p~n", [Packet]),
    
    %% 2) 解析固定头
    {Header, Rest0} = parse_header(Packet),
    io:format("2. 解析固定头:~n   Type=~p, QoS=~p, Retain=~p~n", 
              [maps:get(type,Header), maps:get(qos,Header), maps:get(retain,Header)]),
    
    %% 3) 解析剩余长度
    {Len, Rest1} = parse_remaining_len(Rest0),
    io:format("3. 剩余长度: ~p bytes~n", [Len]),
    
    %% 4) 解析 CONNECT 报文
    {ok, ConnPkt} = parse_connect(Packet),
    io:format("4. 解析 CONNECT:~n   ProtoVer=~p, ClientId=~ts, KeepAlive=~p~n",
              [maps:get(proto_ver,ConnPkt), maps:get(clientid,ConnPkt), 
               maps:get(keepalive,ConnPkt)]),
    
    %% 5) 使用序列化函数
    Serialized = serialize_connect(#{clientid => <<"serialized_demo">>, 
                                     keepalive => 60}),
    io:format("5. 序列化 CONNECT:~n   ~p~n", [Serialized]),
    
    %% 6) 反序列化回去验证
    {ok, Parsed} = parse_connect(iolist_to_binary(Serialized)),
    io:format("6. 反序列化验证:~n   ClientId=~ts, KeepAlive=~p~n",
              [maps:get(clientid,Parsed), maps:get(keepalive,Parsed)]),
    
    io:format("~n✅ 帧解析设计模式: 二进制模式匹配 + continuation 增量解析~n"),
    io:format("   这正 emqtt_frame.erl (788行) 的核心设计~n").
