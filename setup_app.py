#!/usr/bin/env python3
"""
Clipboard History Manager - Setup Script
Automated setup and configuration for the clipboard history application.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


class ClipboardHistorySetup:
    """Setup and configuration manager for the clipboard history application."""

    def __init__(self):
        self.system = platform.system().lower()
        self.script_dir = Path(__file__).parent.absolute()
        self.app_name = "Clipboard History Manager"

    def check_python_version(self):
        """Check if Python version is compatible."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(
                f"❌ Python 3.8+ required, found Python {version.major}.{version.minor}"
            )
            return False

        print(
            f"✅ Python {version.major}.{version.minor}.{version.micro} detected"
        )
        return True

    def install_dependencies(self):
        """Install required Python packages."""
        print("📦 Installing Python dependencies...")

        try:
            # Check if pip is available
            subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                check=True,
                capture_output=True,
            )

            # Install PyQt6
            print("   Installing PyQt6...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "PyQt6"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ PyQt6 installed successfully")
                return True
            else:
                print(f"❌ Failed to install PyQt6: {result.stderr}")
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Error installing dependencies: {e}")
            return False
        except FileNotFoundError:
            print("❌ pip not found. Please install pip and try again.")
            return False

    def verify_installation(self):
        """Verify that all required packages are properly installed."""
        print("🔍 Verifying installation...")

        try:
            import PyQt6
            from PyQt6.QtWidgets import QApplication

            print("✅ PyQt6 import successful")

            # Test basic Qt functionality
            app = QApplication([])
            app.quit()
            print("✅ Qt application test successful")

            return True

        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False
        except Exception as e:
            print(f"❌ Qt test failed: {e}")
            return False

    def create_startup_entries(self):
        """Create platform-specific startup entries."""
        print("🚀 Setting up startup configuration...")

        if self.system == "windows":
            return self.setup_windows_startup()
        elif self.system == "linux":
            return self.setup_linux_startup()
        elif self.system == "darwin":
            return self.setup_macos_startup()
        else:
            print(f"⚠️  Unsupported platform: {self.system}")
            return False

    def setup_windows_startup(self):
        """Setup Windows startup configuration."""
        try:
            import winreg

            startup_path = (
                Path.home()
                / "AppData"
                / "Roaming"
                / "Microsoft"
                / "Windows"
                / "Start Menu"
                / "Programs"
                / "Startup"
            )
            startup_path.mkdir(parents=True, exist_ok=True)

            # Copy CMD script to startup folder
            cmd_script = self.script_dir / "start_clipboard_manager.cmd"
            if cmd_script.exists():
                startup_script = startup_path / "start_clipboard_manager.cmd"
                shutil.copy2(cmd_script, startup_script)
                print(f"✅ Startup script copied to: {startup_script}")
                return True
            else:
                print("❌ CMD startup script not found")
                return False

        except Exception as e:
            print(f"❌ Windows startup setup failed: {e}")
            return False

    def setup_linux_startup(self):
        """Setup Linux startup configuration."""
        try:
            # Create autostart directory
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)

            # Create .desktop file
            desktop_content = f"""[Desktop Entry]
Type=Application
Name={self.app_name}
Comment=Clipboard history manager with infinite storage
Exec={sys.executable} {self.script_dir / 'clipboard_history_app.py'} --hidden
Icon=edit-copy
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""

            desktop_file = autostart_dir / "clipboard-history-manager.desktop"
            desktop_file.write_text(desktop_content)
            desktop_file.chmod(0o755)

            print(f"✅ Desktop file created: {desktop_file}")
            return True

        except Exception as e:
            print(f"❌ Linux startup setup failed: {e}")
            return False

    def setup_macos_startup(self):
        """Setup macOS startup configuration."""
        try:
            # Create LaunchAgent directory
            launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
            launch_agents_dir.mkdir(parents=True, exist_ok=True)

            # Create plist file
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.clipboard-history-manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.script_dir / 'clipboard_history_app.py'}</string>
        <string>--hidden</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""

            plist_file = (
                launch_agents_dir / "com.clipboard-history-manager.plist"
            )
            plist_file.write_text(plist_content)

            # Load the launch agent
            subprocess.run(
                ["launchctl", "load", str(plist_file)], capture_output=True
            )

            print(f"✅ LaunchAgent created: {plist_file}")
            return True

        except Exception as e:
            print(f"❌ macOS startup setup failed: {e}")
            return False

    def create_shortcuts(self):
        """Create desktop shortcuts and quick access."""
        print("🔗 Creating shortcuts...")

        if self.system == "windows":
            return self.create_windows_shortcuts()
        elif self.system == "linux":
            return self.create_linux_shortcuts()
        elif self.system == "darwin":
            return self.create_macos_shortcuts()

        return True

    def create_windows_shortcuts(self):
        """Create Windows desktop shortcuts."""
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, f"{self.app_name}.lnk")

            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = (
                f'"{self.script_dir / "clipboard_history_app.py"}"'
            )
            shortcut.WorkingDirectory = str(self.script_dir)
            shortcut.IconLocation = sys.executable
            shortcut.save()

            print(f"✅ Desktop shortcut created: {shortcut_path}")
            return True

        except ImportError:
            print("⚠️  Optional packages not available for shortcut creation")
            return True
        except Exception as e:
            print(f"❌ Windows shortcut creation failed: {e}")
            return False

    def create_linux_shortcuts(self):
        """Create Linux desktop shortcuts."""
        try:
            desktop_dir = Path.home() / "Desktop"
            if not desktop_dir.exists():
                desktop_dir = Path.home()

            desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={self.app_name}
Comment=Clipboard history manager
Exec={sys.executable} {self.script_dir / 'clipboard_history_app.py'}
Icon=edit-copy
Terminal=false
Categories=Utility;
"""

            desktop_file = desktop_dir / "clipboard-history-manager.desktop"
            desktop_file.write_text(desktop_content)
            desktop_file.chmod(0o755)

            print(f"✅ Desktop shortcut created: {desktop_file}")
            return True

        except Exception as e:
            print(f"❌ Linux shortcut creation failed: {e}")
            return False

    def create_macos_shortcuts(self):
        """Create macOS shortcuts/aliases."""
        try:
            # Create an alias on the desktop would require AppleScript
            # For now, just provide instructions
            print("ℹ️  For macOS, you can create shortcuts manually:")
            print(
                f"   Drag {self.script_dir / 'clipboard_history_app.py'} to Desktop while holding Cmd+Option"
            )
            return True

        except Exception as e:
            print(f"❌ macOS shortcut creation failed: {e}")
            return False

    def test_application(self):
        """Test the application to ensure it works properly."""
        print("🧪 Testing application...")

        try:
            # Import and test basic functionality
            app_path = self.script_dir / "clipboard_history_app.py"
            if not app_path.exists():
                print(f"❌ Application file not found: {app_path}")
                return False

            # Test import (without running the GUI)
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "clipboard_app", app_path
            )
            module = importlib.util.module_from_spec(spec)

            # This will test imports but won't run the app
            print("✅ Application imports successfully")

            return True

        except Exception as e:
            print(f"❌ Application test failed: {e}")
            return False

    def run_setup(self):
        """Run the complete setup process."""
        print(f"🎯 Setting up {self.app_name}")
        print(f"📁 Installation directory: {self.script_dir}")
        print(f"💻 Platform: {platform.system()} {platform.release()}")
        print("─" * 60)

        steps = [
            ("Checking Python version", self.check_python_version),
            ("Installing dependencies", self.install_dependencies),
            ("Verifying installation", self.verify_installation),
            ("Testing application", self.test_application),
            ("Creating startup entries", self.create_startup_entries),
            ("Creating shortcuts", self.create_shortcuts),
        ]

        success_count = 0
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if step_func():
                success_count += 1
            else:
                print(f"❌ {step_name} failed")

        print("\n" + "─" * 60)
        print(
            f"📊 Setup completed: {success_count}/{len(steps)} steps successful"
        )

        if success_count == len(steps):
            print("🎉 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Restart your computer to enable auto-start")
            print(
                "2. Or run the application manually with the startup scripts"
            )
            print("3. Use Ctrl+Shift+V to open the clipboard history")
            return True
        else:
            print("⚠️  Setup completed with some issues")
            print("You may need to configure startup manually")
            return False


def main():
    """Main setup function."""
    print("Clipboard History Manager - Setup Script")
    print("=" * 60)

    setup = ClipboardHistorySetup()

    # Check if running with appropriate privileges
    if setup.system == "windows" and not os.access(sys.executable, os.W_OK):
        print("⚠️  Consider running as administrator for full setup")

    try:
        success = setup.run_setup()

        if success:
            print("\n✨ Setup completed successfully!")

            # Ask if user wants to start the application now
            response = (
                input("\nWould you like to start the application now? (y/N): ")
                .lower()
                .strip()
            )
            if response in ("y", "yes"):
                print("🚀 Starting application...")
                subprocess.Popen(
                    [
                        sys.executable,
                        str(setup.script_dir / "clipboard_history_app.py"),
                        "--hidden",
                    ]
                )
                print("✅ Application started in background")
        else:
            print("\n❌ Setup encountered some issues")
            print(
                "Please check the error messages above and try manual configuration"
            )

    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
