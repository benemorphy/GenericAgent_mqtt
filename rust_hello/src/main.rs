fn main() {
    println!("Rust {} ready!", env!("CARGO_PKG_RUST_VERSION"));
    println!("Project: {} v{}", env!("CARGO_PKG_NAME"), env!("CARGO_PKG_VERSION"));
    // 未来: BoardService高吞吐模块 / MQTT引擎 / 查询处理
}
