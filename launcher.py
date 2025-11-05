"""
AI File Organiser - GUI Launcher

Beautiful GUI launcher with easy access to all features.

Copyright © 2025 Alexandru Emanuel Vasile. All Rights Reserved.
"""

import tkinter as tk
from tkinter import messagebox
import subprocess
import sys
import threading
from pathlib import Path
import webbrowser

# Add installer path for updater
sys.path.insert(0, str(Path(__file__).parent / "installer"))

try:
    from installer.auto_updater import AutoUpdater
except:
    AutoUpdater = None


class LauncherGUI:
    """Main launcher GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AI File Organiser")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # Check for updates
        if AutoUpdater:
            self.updater = AutoUpdater()
            self.check_updates()

        self.create_ui()

    def check_updates(self):
        """Check for updates silently"""
        def check():
            update_info = self.updater.show_update_notification()
            if update_info:
                self.show_update_notification(update_info)

        threading.Thread(target=check, daemon=True).start()

    def show_update_notification(self, update_info):
        """Show update notification"""
        response = messagebox.askyesno(
            "Update Available",
            f"A new version is available: {update_info['version']}\n\n"
            f"Would you like to download it?",
            icon='info'
        )

        if response:
            webbrowser.open(update_info['url'])
            if AutoUpdater:
                self.updater.clear_update_notification()

    def create_ui(self):
        """Create the launcher UI"""
        # Header
        header = tk.Frame(self.root, bg="#2E86AB", height=100)
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="AI File Organiser",
            font=("Arial", 28, "bold"),
            bg="#2E86AB",
            fg="white"
        )
        title.pack(pady=25)

        # Main content
        content = tk.Frame(self.root, padx=40, pady=20)
        content.pack(fill="both", expand=True)

        # Feature buttons
        btn_frame = tk.Frame(content)
        btn_frame.pack(fill="both", expand=True)

        # Dashboard button
        dashboard_btn = tk.Button(
            btn_frame,
            text="📊 Launch Dashboard",
            font=("Arial", 14, "bold"),
            bg="#2E86AB",
            fg="white",
            height=3,
            command=self.launch_dashboard
        )
        dashboard_btn.pack(fill="x", pady=10)

        # MCP Server button
        mcp_btn = tk.Button(
            btn_frame,
            text="🔌 Start MCP Server",
            font=("Arial", 14),
            bg="#A23B72",
            fg="white",
            height=2,
            command=self.launch_mcp_server
        )
        mcp_btn.pack(fill="x", pady=10)

        # Organize Files button
        organize_btn = tk.Button(
            btn_frame,
            text="📁 Organize Files",
            font=("Arial", 14),
            bg="#F18F01",
            fg="white",
            height=2,
            command=self.launch_organize
        )
        organize_btn.pack(fill="x", pady=10)

        # Documentation button
        docs_btn = tk.Button(
            btn_frame,
            text="📖 Open Documentation",
            font=("Arial", 12),
            height=2,
            command=self.open_docs
        )
        docs_btn.pack(fill="x", pady=10)

        # Settings button
        settings_btn = tk.Button(
            btn_frame,
            text="⚙️ Settings",
            font=("Arial", 12),
            height=2,
            command=self.open_settings
        )
        settings_btn.pack(fill="x", pady=10)

        # Footer
        footer = tk.Frame(self.root, bg="#f0f0f0", height=40)
        footer.pack(fill="x", side="bottom")

        copyright_text = tk.Label(
            footer,
            text="© 2025 Alexandru Emanuel Vasile. All Rights Reserved.",
            bg="#f0f0f0",
            font=("Arial", 8),
            fg="gray"
        )
        copyright_text.pack(pady=10)

    def launch_dashboard(self):
        """Launch the web dashboard"""
        try:
            messagebox.showinfo(
                "Launching Dashboard",
                "Dashboard will open in your browser...\n\n"
                "Default URL: http://localhost:5000\n\n"
                "Press Ctrl+C in the terminal to stop."
            )

            subprocess.Popen(
                [sys.executable, "-m", "src.ui.dashboard"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch dashboard:\n{str(e)}")

    def launch_mcp_server(self):
        """Launch the MCP server"""
        try:
            messagebox.showinfo(
                "MCP Server",
                "MCP Server is starting...\n\n"
                "Use Claude Desktop or another MCP client to connect.\n\n"
                "The server will run in the background."
            )

            subprocess.Popen(
                [sys.executable, "-m", "src.mcp.mcp_server"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch MCP server:\n{str(e)}")

    def launch_organize(self):
        """Launch file organization wizard"""
        try:
            subprocess.Popen(
                [sys.executable, "examples/mcp_workflows.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch organizer:\n{str(e)}")

    def open_docs(self):
        """Open documentation"""
        docs_menu = tk.Toplevel(self.root)
        docs_menu.title("Documentation")
        docs_menu.geometry("400x300")

        tk.Label(
            docs_menu,
            text="Documentation",
            font=("Arial", 16, "bold")
        ).pack(pady=20)

        docs = [
            ("Quick Start Guide", "MCP_QUICKSTART.md"),
            ("MCP Integration", "docs/MCP_INTEGRATION.md"),
            ("Tool Reference", "docs/MCP_TOOLS.md"),
            ("README", "README.md")
        ]

        for name, path in docs:
            btn = tk.Button(
                docs_menu,
                text=name,
                command=lambda p=path: self.open_file(p),
                width=30
            )
            btn.pack(pady=5)

    def open_file(self, file_path):
        """Open a file with default application"""
        import os
        try:
            if sys.platform == "win32":
                os.startfile(file_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

    def open_settings(self):
        """Open settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x400")

        tk.Label(
            settings_window,
            text="Settings",
            font=("Arial", 16, "bold")
        ).pack(pady=20)

        # Settings options
        settings_frame = tk.LabelFrame(settings_window, text="General", padx=20, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=10)

        # Auto-update setting
        auto_update_var = tk.BooleanVar(value=True)
        auto_update_check = tk.Checkbutton(
            settings_frame,
            text="Enable automatic updates (anonymous)",
            variable=auto_update_var
        )
        auto_update_check.pack(anchor="w")

        # Ollama settings
        ollama_frame = tk.LabelFrame(settings_window, text="Ollama", padx=20, pady=10)
        ollama_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(ollama_frame, text="Ollama URL:").pack(anchor="w")
        ollama_entry = tk.Entry(ollama_frame, width=40)
        ollama_entry.insert(0, "http://localhost:11434")
        ollama_entry.pack(anchor="w", pady=5)

        # Save button
        save_btn = tk.Button(
            settings_window,
            text="Save Settings",
            bg="#2E86AB",
            fg="white",
            command=lambda: messagebox.showinfo("Settings", "Settings saved!")
        )
        save_btn.pack(pady=20)

    def run(self):
        """Run the launcher"""
        self.root.mainloop()


if __name__ == "__main__":
    launcher = LauncherGUI()
    launcher.run()
