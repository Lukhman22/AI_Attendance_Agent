// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use tauri::{State, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandEvent, CommandChild};

struct BackendState {
    port: Mutex<Option<u16>>,
    process: Mutex<Option<CommandChild>>,
}

#[tauri::command]
fn get_backend_port(state: State<BackendState>) -> Result<u16, String> {
    let port = state.port.lock().unwrap();
    port.ok_or_else(|| "Backend port not yet available".to_string())
}

#[tauri::command]
fn get_backend_log_path(app: tauri::AppHandle) -> Result<String, String> {
    let log_path = app.path().app_log_dir().expect("no log dir").join("backend.log");
    Ok(log_path.to_string_lossy().into_owned())
}

fn main() {
    let state = BackendState {
        port: Mutex::new(None),
        process: Mutex::new(None),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![get_backend_port, get_backend_log_path])
        .manage(state)
        .setup(|app| {
            let resource_path = app
                .path()
                .resource_dir()
                .expect("failed to get resource dir");
            
            let exe_name = if cfg!(target_os = "windows") {
                "backend.exe"
            } else {
                "backend"
            };
            
            let backend_exe = resource_path.join("backend").join(exe_name);
            
            let log_path = app.path().app_log_dir().expect("no log dir").join("backend.log");
            std::fs::create_dir_all(log_path.parent().unwrap()).unwrap();
            
            let mut log_file = std::fs::OpenOptions::new().create(true).append(true).open(&log_path).unwrap();
            use std::io::Write;
            writeln!(log_file, "--- Starting backend from {:?} ---", backend_exe).ok();

            if !backend_exe.exists() {
                let msg = format!("Error: Backend executable not found at {:?}", backend_exe);
                println!("{}", msg);
                writeln!(log_file, "{}", msg).ok();
                return Ok(());
            }

            let command = app.shell().command(backend_exe.to_string_lossy().to_string());
            
            let (mut rx, child) = match command.spawn() {
                Ok(res) => res,
                Err(err) => {
                    let msg = format!("Failed to spawn backend process: {}", err);
                    println!("{}", msg);
                    writeln!(log_file, "{}", msg).ok();
                    return Ok(());
                }
            };

            let app_handle = app.handle().clone();
            
            tauri::async_runtime::spawn(async move {
                let mut thread_log = std::fs::OpenOptions::new().create(true).append(true).open(&log_path).unwrap();
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                            let line_str = String::from_utf8_lossy(&line);
                            println!("Backend: {}", line_str);
                            writeln!(thread_log, "{}", line_str).ok();
                            if line_str.contains("__TAURI_BACKEND_PORT__=") {
                                let parts: Vec<&str> = line_str.split("__TAURI_BACKEND_PORT__=").collect();
                                if parts.len() > 1 {
                                    let port_str = parts[1].trim();
                                    if let Ok(port) = port_str.parse::<u16>() {
                                        let state = app_handle.state::<BackendState>();
                                        *state.port.lock().unwrap() = Some(port);
                                        let msg = format!("Backend is ready on port {}", port);
                                        println!("{}", msg);
                                        writeln!(thread_log, "{}", msg).ok();
                                    }
                                }
                            }
                        }
                        CommandEvent::Error(err) => {
                            let msg = format!("Backend Error: {}", err);
                            println!("{}", msg);
                            writeln!(thread_log, "{}", msg).ok();
                        }
                        CommandEvent::Terminated(payload) => {
                            let msg = format!("Backend Terminated: {:?}", payload);
                            println!("{}", msg);
                            writeln!(thread_log, "{}", msg).ok();
                        }
                        _ => {}
                    }
                }
            });

            let state_binding = app.state::<BackendState>();
            let mut state_proc = state_binding.process.lock().unwrap();
            *state_proc = Some(child);

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendState>();
                let mut process = state.process.lock().unwrap();
                if let Some(child) = process.take() {
                    let _ = child.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
