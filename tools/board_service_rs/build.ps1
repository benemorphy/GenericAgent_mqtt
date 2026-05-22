Set-Location 'D:\open_claw_agent\GenericAgent_mqtt\tools\board_service_rs'
$env:RUST_LOG='info'
cargo build --release 2>&1 | Out-File -FilePath build.log
