// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use tauri::Manager;

#[derive(Debug, Serialize, Deserialize)]
struct FileItem {
    path: String,
    name: String,
    size: u64,
    modified: String,
    category: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct ClassificationResult {
    category: String,
    subcategory: Option<String>,
    confidence: f32,
    suggested_path: String,
    suggested_name: Option<String>,
    tags: Vec<String>,
    summary: Option<String>,
    reasoning: Option<String>,
    model_used: String,
    processing_time_ms: u32,
    tokens_used: u32,
    cost_usd: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct OrganizeOptions {
    folder: String,
    preview: bool,
    auto_approve: bool,
    deep_analysis: bool,
    use_multi_model: bool,
    user_tier: String,
}

/// Call Python backend to classify a file
#[tauri::command]
async fn classify_file(file_path: String, use_multi_model: bool, tier: String) -> Result<ClassificationResult, String> {
    // Get the path to the Python script
    let project_root = std::env::current_dir()
        .map_err(|e| format!("Failed to get current directory: {}", e))?;

    let python_script = project_root
        .parent()
        .ok_or("Failed to get parent directory")?
        .join("src")
        .join("cli")
        .join("classify_single.py");

    if !python_script.exists() {
        return Err(format!("Python script not found at: {:?}", python_script));
    }

    // Build Python command
    let mut cmd = Command::new("python3");
    cmd.arg(python_script)
        .arg("--file")
        .arg(&file_path)
        .arg("--json");

    if use_multi_model {
        cmd.arg("--multi-model").arg("--tier").arg(&tier);
    }

    // Execute command
    let output = cmd.output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python script failed: {}", stderr));
    }

    // Parse JSON output
    let stdout = String::from_utf8_lossy(&output.stdout);
    serde_json::from_str(&stdout)
        .map_err(|e| format!("Failed to parse JSON: {}", e))
}

/// Call Python backend to organize a folder
#[tauri::command]
async fn organize_folder(options: OrganizeOptions) -> Result<String, String> {
    let project_root = std::env::current_dir()
        .map_err(|e| format!("Failed to get current directory: {}", e))?;

    let python_script = project_root
        .parent()
        .ok_or("Failed to get parent directory")?
        .join("src")
        .join("cli")
        .join("commands.py");

    if !python_script.exists() {
        return Err(format!("Python script not found at: {:?}", python_script));
    }

    // Build Python command
    let mut cmd = Command::new("python3");
    cmd.arg(python_script)
        .arg("organize")
        .arg(&options.folder);

    if options.preview {
        cmd.arg("--preview");
    }
    if options.auto_approve {
        cmd.arg("--auto");
    }
    if options.deep_analysis {
        cmd.arg("--deep");
    }
    if options.use_multi_model {
        cmd.arg("--multi-model").arg("--tier").arg(&options.user_tier);
    }

    // Execute command
    let output = cmd.output()
        .map_err(|e| format!("Failed to execute Python: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Organization failed: {}", stderr));
    }

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

/// Get list of files in a directory
#[tauri::command]
async fn list_files(directory: String) -> Result<Vec<FileItem>, String> {
    let path = PathBuf::from(&directory);

    if !path.exists() {
        return Err(format!("Directory does not exist: {}", directory));
    }

    let mut files = Vec::new();

    match std::fs::read_dir(&path) {
        Ok(entries) => {
            for entry in entries {
                if let Ok(entry) = entry {
                    if let Ok(metadata) = entry.metadata() {
                        if metadata.is_file() {
                            let file_name = entry.file_name().to_string_lossy().to_string();
                            let file_path = entry.path().to_string_lossy().to_string();

                            let modified = metadata.modified()
                                .map(|t| format!("{:?}", t))
                                .unwrap_or_else(|_| "Unknown".to_string());

                            files.push(FileItem {
                                path: file_path,
                                name: file_name,
                                size: metadata.len(),
                                modified,
                                category: None,
                            });
                        }
                    }
                }
            }
        }
        Err(e) => return Err(format!("Failed to read directory: {}", e)),
    }

    Ok(files)
}

/// Open file explorer at path
#[tauri::command]
async fn open_in_explorer(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open explorer: {}", e))?;
    }

    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open finder: {}", e))?;
    }

    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| format!("Failed to open file manager: {}", e))?;
    }

    Ok(())
}

/// Get system information
#[tauri::command]
async fn get_system_info() -> Result<serde_json::Value, String> {
    Ok(serde_json::json!({
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "family": std::env::consts::FAMILY,
    }))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            classify_file,
            organize_folder,
            list_files,
            open_in_explorer,
            get_system_info,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
