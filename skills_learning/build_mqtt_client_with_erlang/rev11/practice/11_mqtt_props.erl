%%%===================================================================
%%% Exercise 11: MQTT v5 属性编码器 — 基于 emqtt_props 的设计模式
%%% 演示: Erlang 模式匹配实现 MQTT v5 30+ 种属性序列化
%%% 原理: emqtt 用 serialize_property/2 匹配每种的ID码
%%% 编译: erlc 11_mqtt_props.erl
%%% 运行: erl -noshell -s 11_mqtt_props test -s init stop
%%%===================================================================
-module('11_mqtt_props').
-export([serialize_property/2, serialize_properties/1, parse_properties/1,
         test/0]).

%% MQTT v5 属性 ID 码
-define(PAYLOAD_FORMAT_IND,       16#01).
-define(MESSAGE_EXPIRY_INTERVAL,  16#02).
-define(CONTENT_TYPE,             16#03).
-define(RESPONSE_TOPIC,           16#08).
-define(CORRELATION_DATA,         16#09).
-define(SUBSCRIPTION_ID,          16#0B).
-define(SESSION_EXPIRY_INTERVAL,  16#11).
-define(SERVER_KEEP_ALIVE,        16#13).
-define(AUTH_METHOD,              16#15).
-define(AUTH_DATA,                16#16).
-define(USER_PROPERTY,            16#26).
-define(MAXIMUM_PACKET_SIZE,      16#27).

%% ============ 序列化 ============

%% 序列化属性列表 (Map → Binary)
serialize_properties(undefined) -> <<0>>;
serialize_properties(Props) when map_size(Props) =:= 0 -> <<0>>;
serialize_properties(Props) when is_map(Props) ->
    Bin = << <<(serialize_property(Prop, Val))/binary>> 
              || {Prop, Val} <- maps:to_list(Props) >>,
    [encode_vbi(byte_size(Bin)), Bin].

%% 每种属性有固定 ID 码 —— 模式匹配确保完整性
serialize_property('Payload-Format-Indicator', Val) ->
    <<?PAYLOAD_FORMAT_IND, Val>>;
serialize_property('Message-Expiry-Interval', Val) ->
    <<?MESSAGE_EXPIRY_INTERVAL, Val:32/big>>;
serialize_property('Content-Type', Val) ->
    <<?CONTENT_TYPE, (encode_utf8(Val))/binary>>;
serialize_property('Response-Topic', Val) ->
    <<?RESPONSE_TOPIC, (encode_utf8(Val))/binary>>;
serialize_property('Correlation-Data', Val) when is_binary(Val) ->
    <<?CORRELATION_DATA, (byte_size(Val)):16/big, Val/binary>>;
serialize_property('Subscription-Identifier', Val) ->
    <<?SUBSCRIPTION_ID, (encode_vbi(Val))/binary>>;
serialize_property('Session-Expiry-Interval', Val) ->
    <<?SESSION_EXPIRY_INTERVAL, Val:32/big>>;
serialize_property('Server-Keep-Alive', Val) ->
    <<?SERVER_KEEP_ALIVE, Val:16/big>>;
serialize_property('Authentication-Method', Val) ->
    <<?AUTH_METHOD, (encode_utf8(Val))/binary>>;
serialize_property('Authentication-Data', Val) ->
    <<?AUTH_DATA, (iolist_size(Val)):16/big, Val/binary>>;
serialize_property('User-Property', {Key, Val}) ->
    <<?USER_PROPERTY, (encode_utf8(Key))/binary, (encode_utf8(Val))/binary>>;
serialize_property('User-Property', Props) when is_list(Props) ->
    << <<(serialize_property('User-Property', {K, V}))/binary>> 
         || {K, V} <- Props >>;
serialize_property('Maximum-Packet-Size', Val) ->
    <<?MAXIMUM_PACKET_SIZE, Val:32/big>>;
serialize_property(_, undefined) -> <<>>.

%% ============ 解析 ============
parse_properties(<<0, Rest/binary>>) -> {#{}, Rest};
parse_properties(Bin) ->
    {Len, Rest} = decode_vbi(Bin),
    <<PropBin:Len/binary, Rest2/binary>> = Rest,
    {parse_prop_map(PropBin, #{}), Rest2}.

parse_prop_map(<<>>, Acc) -> Acc;
parse_prop_map(<<?PAYLOAD_FORMAT_IND, Val, Rest/binary>>, Acc) ->
    parse_prop_map(Rest, Acc#{'Payload-Format-Indicator' => Val});
parse_prop_map(<<?MESSAGE_EXPIRY_INTERVAL, Val:32/big, Rest/binary>>, Acc) ->
    parse_prop_map(Rest, Acc#{'Message-Expiry-Interval' => Val});
parse_prop_map(<<?SESSION_EXPIRY_INTERVAL, Val:32/big, Rest/binary>>, Acc) ->
    parse_prop_map(Rest, Acc#{'Session-Expiry-Interval' => Val});
parse_prop_map(<<?SERVER_KEEP_ALIVE, Val:16/big, Rest/binary>>, Acc) ->
    parse_prop_map(Rest, Acc#{'Server-Keep-Alive' => Val});
parse_prop_map(<<?MAXIMUM_PACKET_SIZE, Val:32/big, Rest/binary>>, Acc) ->
    parse_prop_map(Rest, Acc#{'Maximum-Packet-Size' => Val});
parse_prop_map(<<?USER_PROPERTY, Rest/binary>>, Acc) ->
    {Key, Rest1} = decode_utf8(Rest),
    {Val, Rest2} = decode_utf8(Rest1),
    parse_prop_map(Rest2, Acc#{'User-Property' => {Key, Val}});
parse_prop_map(<<_Id, _/binary>>, Acc) -> Acc.

%% ============ 编解码工具 ============

%% Variable Byte Integer 编码
encode_vbi(N) when N =< 127 -> <<0:1, N:7>>;
encode_vbi(N) -> <<1:1, (N rem 128):7, (encode_vbi(N div 128))/binary>>.

%% Variable Byte Integer 解码
decode_vbi(<<0:1, V:7, Rest/binary>>) -> {V, Rest};
decode_vbi(<<1:1, V:7, Rest/binary>>) -> 
    {More, Rest2} = decode_vbi(Rest),
    {V + More * 128, Rest2}.

%% UTF-8 字符串编解码
encode_utf8(S) ->
    Bin = unicode:characters_to_binary(S),
    <<(byte_size(Bin)):16/big, Bin/binary>>.

decode_utf8(<<Len:16/big, Str:Len/binary, Rest/binary>>) -> {Str, Rest}.

%% ============ 测试 ============
test() ->
    io:format("=== MQTT v5 属性编解码演示 ===~n~n"),
    
    %% 1) 构建属性 Map
    Props = #{
        'Session-Expiry-Interval' => 3600,
        'Server-Keep-Alive' => 30,
        'Maximum-Packet-Size' => 1048576,
        'Payload-Format-Indicator' => 1,
        'User-Property' => {<<"type">>, <<"demo">>}
    },
    io:format("1. 原始属性:~n   ~p~n", [Props]),
    
    %% 2) 序列化
    Bin = serialize_properties(Props),
    io:format("2. 序列化 (~p bytes):~n   ~p~n", [iolist_size(Bin), Bin]),
    
    %% 3) 反序列化 (转成flat binary)
    FlatBin = iolist_to_binary(Bin),
    {Parsed, _} = parse_properties(FlatBin),
    io:format("3. 反序列化:~n   ~p~n", [Parsed]),
    
    %% 4) 验证往返
    case maps:get('Session-Expiry-Interval', Parsed) of
        3600 -> io:format("   ✅ Session-Expiry-Interval = 3600~n");
        _    -> io:format("   ❌ 不匹配~n")
    end,
    case maps:get('Server-Keep-Alive', Parsed) of
        30 -> io:format("   ✅ Server-Keep-Alive = 30~n");
        _  -> io:format("   ❌ 不匹配~n")
    end,
    
    io:format("~n✅ MQTT v5 属性设计模式: 每种属性模式匹配固定ID码~n"),
    io:format("   emqtt_props 定义了 30+ 种属性的序列化规则~n").
