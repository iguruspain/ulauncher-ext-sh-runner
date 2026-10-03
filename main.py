#!/usr/bin/env python3

import os
import subprocess
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

class ScriptRunner(Extension):
    def __init__(self):
        super(ScriptRunner, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def expand_path(self, path):
        if not path:
            return ""
        return os.path.expanduser(os.path.expandvars(path))

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        items = []
        # Pecah query menjadi kata-kata kecil dan hapus spasi kosong
        query_parts = (event.get_argument() or "").lower().split()
        
        raw_paths = extension.preferences['scripts_dir'].split(',')
        all_scripts = []
        supported_ext = ('.sh', '.py')
        
        for p in raw_paths:
            p = p.strip()
            if not p or p.startswith('!'):
                continue
            
            scripts_dir = extension.expand_path(p)
            if os.path.exists(scripts_dir):
                try:
                    for f in os.listdir(scripts_dir):
                        if f.lower().endswith(supported_ext):
                            all_scripts.append({
                                "filename": f,
                                "full_path": os.path.join(scripts_dir, f)
                            })
                except Exception:
                    continue

        # Logika Pencarian: Cek apakah SEMUA kata kunci dalam query ada di nama file
        filtered = []
        for s in all_scripts:
            filename_lower = s['filename'].lower()
            # Jika semua bagian query (misal: 'sh' dan 'my') ada di nama file
            if all(part in filename_lower for part in query_parts):
                filtered.append(s)
        
        # Batasi hasil 10 teratas
        filtered = filtered[:10]

        if not filtered and not query_parts:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png', 
                    name="No scripts found", 
                    description="Add .sh or .py files to your configured directories."
                )
            ])

        for script in filtered:
            file_ext = os.path.splitext(script['filename'])[1]
            display_name = os.path.splitext(script['filename'])[0].replace('-', ' ').replace('_', ' ').title()
            
            items.append(ExtensionResultItem(
                icon='images/icon.png',
                name=f"[{file_ext[1:].upper()}] {display_name}",
                description=f"Run: {script['full_path']}",
                on_enter=ExtensionCustomAction(script['full_path'])
            ))

        return RenderResultListAction(items)

class ItemEnterEventListener(EventListener):
    def run_terminal_command(self, terminal, working_dir, command=None):
        # 1. Konsole (KDE)
        if "konsole" in terminal:
            args = [terminal, "--workdir", working_dir]
            if command: args += ["-e", "bash", "-ic", command]
            else: args += ["-e", "bash"]
            subprocess.Popen(args)

        # 2. XFCE4 Terminal
        elif "xfce4-terminal" in terminal:
            full_command = f"bash -ic \"{command}\""
            args = [terminal, "--working-directory", working_dir, "-e", full_command]
            subprocess.Popen(args)

        # 3. Terminator
        elif "terminator" in terminal:
            args = [terminal, "--working-directory", working_dir]
            if command: args += ["-x", "bash", "-ic", command]
            else: args += ["-x", "bash"]
            subprocess.Popen(args)

        # 4. Ghostty terminal ()
        elif "ghostty" in terminal:
            args = [terminal, f"--working-directory={working_dir}"]
            if command: args += ["-e", "bash", "-ic", command]
            else: args += ["-e", "bash"]
            subprocess.Popen(args)

        # 5. Kitty
        elif "kitty" in terminal:
            args = [terminal, "--directory", working_dir]
            if command: args += ["bash", "-ic", command]
            else: args += ["bash"]
            subprocess.Popen(args)

        # 6. GNOME Terminal / Default
        else:
            args = [terminal, "--working-directory", working_dir, "--"]
            if command: args += ["bash", "-ic", command]
            else: args += ["bash"]
            subprocess.Popen(args)

    def on_event(self, event, extension):
        script_path = event.get_data()
        working_dir = os.path.dirname(script_path) 
        terminal = extension.expand_path(extension.preferences['terminal_emulator'])
        py_cmd = extension.preferences.get('python_command', 'python3')

        # Logika pemilihan command berdasarkan ekstensi
        if script_path.endswith('.py'):
            exec_command = f"{py_cmd} '{script_path}'"
        else:
            exec_command = f"chmod +x '{script_path}'; '{script_path}'"
        
        # Gabungkan dengan penahan (hold) agar terminal tidak langsung tutup
        full_cmd = (
            f"{exec_command}; "
            f"echo -e '\\n--- Script Finished ---'; "
            f"read -p 'Press Enter to close...'"
        )

        self.run_terminal_command(terminal, working_dir, command=full_cmd)
        return HideWindowAction()

if __name__ == '__main__':
    ScriptRunner().run()
