


import sys
import os
import subprocess
import time
import ctypes
import random
import json
from ctypes import wintypes
from typing import Optional, Tuple, Dict, Any

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel, QLineEdit,
    QComboBox, QTextEdit, QGroupBox, QHeaderView, QMessageBox, QFileDialog,
    QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QCursor

user32 = ctypes.windll.user32
CONFIG_FILE = "ldplayer_paths.json"


# =====================================================================
# ថ្នាក់គ្រប់គ្រង LDPlayer (Backend Engine)
# =====================================================================
class LDPlayerLauncher:
    def __init__(self, install_dir: str = ""):
        self.set_path(install_dir)

    def set_path(self, install_dir: str):
        """ផ្លាស់ប្តូរ Path LDPlayer (គ្មាន Default Path ទៀតទេ)"""
        self.install_dir = install_dir.strip() if install_dir else ""
        if self.install_dir and os.path.isdir(self.install_dir):
            self.console = os.path.join(self.install_dir, "ldconsole.exe")
            if not os.path.isfile(self.console):
                self.console = os.path.join(self.install_dir, "dnconsole.exe")
        else:
            self.console = ""

    def is_valid(self) -> bool:
        """ពិនិត្យមើលថាតើ Path ត្រូវបានកំណត់ និងមាន Console ពិតប្រាកដឬនៅ"""
        return bool(self.console and os.path.isfile(self.console))

    def _adb_cmd(self, index: int, command: str) -> str:
        if not self.is_valid():
            return ""
        res = subprocess.run(
            [self.console, "adb", "--index", str(index), "--command", command],
            cwd=self.install_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        return res.stdout.strip()

    def _get_random_device(self) -> Tuple[str, str]:
        devices = [
            ("samsung", "SM-S928B"), ("samsung", "SM-S918B"), ("samsung", "SM-F946B"),
            ("XIAOMI", "23127PN0CC"), ("XIAOMI", "2509FPN0BC"), ("Google", "Pixel 9 Pro XL"),
            ("Google", "Pixel 8 Pro"), ("OnePlus", "CPH2581"), ("OPPO", "CPH2505"),
            ("asus", "ASUS_AI2401")
        ]
        return random.choice(devices)

    def _get_window_size(self, hwnd: int) -> Tuple[int, int]:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (rect.right - rect.left), (rect.bottom - rect.top)

    def List(self) -> list[dict]:
        if not self.is_valid():
            return []
        proc = subprocess.run(
            [self.console, "list2"], cwd=self.install_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        instances = []
        for line in proc.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0])
                    name = parts[1]
                    top_hwnd = int(parts[2]) if parts[2].isdigit() else 0
                    is_running = len(parts) >= 5 and int(parts[4]) == 1
                    pid = int(parts[5]) if len(parts) >= 6 and parts[5].isdigit() else 0
                    instances.append({
                        "index": idx, "name": name, "running": is_running,
                        "hwnd": top_hwnd, "pid": pid, "adb_port": f"emulator-{5554 + idx * 2}"
                    })
                except ValueError:
                    pass
        return instances

    def Create(self, name: str, resolution: str = "250,500,100") -> int:
        subprocess.run([self.console, "add", "--name", name], cwd=self.install_dir, capture_output=True, text=True)
        new_idx = 0
        for inst in self.List():
            if inst["name"] == name:
                new_idx = inst["index"]
                break
        
        manu, model = self._get_random_device()
        subprocess.run(
            [
                self.console, "modify", "--index", str(new_idx),
                "--cpu", "2", "--memory", "2048",
                "--resolution", resolution,
                "--manufacturer", manu, "--model", model
            ],
            cwd=self.install_dir, capture_output=True, text=True
        )
        return new_idx

    def Move(self, index: int, start_x: int = 0, start_y: int = 0, timeout: int = 15) -> bool:
        start_time = time.time()
        target_hwnd = None
        running_indices = []

        while time.time() - start_time < timeout:
            running_indices = []
            for inst in self.List():
                if inst["running"] and inst["hwnd"] > 0:
                    running_indices.append(inst["index"])
                    if inst["index"] == index:
                        target_hwnd = inst["hwnd"]
            if target_hwnd:
                break
            time.sleep(0.5)

        if not target_hwnd:
            return False

        real_width, real_height = self._get_window_size(target_hwnd)
        gap = 5
        step_x = real_width + gap
        step_y = real_height + gap
        screen_w = user32.GetSystemMetrics(0)
        max_cols = max(1, screen_w // step_x)

        if len(running_indices) > 1 and index in running_indices:
            order = running_indices.index(index)
            col = order % max_cols
            row = order // max_cols
            final_x = start_x + (col * step_x)
            final_y = start_y + (row * step_y)
        else:
            final_x = start_x
            final_y = start_y

        user32.SetWindowPos(target_hwnd, 0, final_x, final_y, 0, 0, 0x0001 | 0x0004)
        return True

    def ArrangeAll(self, start_x: int = 0, start_y: int = 0) -> None:
        running = [inst for inst in self.List() if inst["running"] and inst["hwnd"] > 0]
        for inst in running:
            self.Move(inst["index"], start_x=start_x, start_y=start_y)

    def Wait(self, index: int, timeout: int = 60) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            res = self._adb_cmd(index, "shell getprop sys.boot_completed")
            if "1" in res:
                return True
            time.sleep(2)
        return False

    def Start(self, index: int) -> None:
        subprocess.run([self.console, "launch", "--index", str(index)], cwd=self.install_dir)
        self.Move(index)
        self.Wait(index)

    def Stop(self, index: int) -> None:
        subprocess.run([self.console, "quit", "--index", str(index)], cwd=self.install_dir)

    def Delete(self, index: int) -> None:
        self.Stop(index)
        time.sleep(1)
        subprocess.run([self.console, "remove", "--index", str(index)], cwd=self.install_dir)

    def SetGPS(self, index: int, city: str) -> None:
        city_db = {
            "phnom penh": (11.5564, 104.9282), "siem reap": (13.3671, 103.8448),
            "new york": (40.7128, -74.0060), "los angeles": (34.0522, -118.2437),
            "bangkok": (13.7563, 100.5018), "tokyo": (35.6762, 139.6503),
            "london": (51.5074, -0.1278), "singapore": (1.3521, 103.8198),
            "dallas": (32.7767, -96.7970), "miami": (25.7617, -80.1918)
        }
        lat, lng = city_db.get(city.lower(), (11.5564, 104.9282))
        subprocess.run([self.console, "locate", "--index", str(index), "--LLI", f"{lng},{lat}"], cwd=self.install_dir)
        self._adb_cmd(index, f"emu geo fix {lng} {lat}")

    def ResetGPS(self, index: int) -> None:
        subprocess.run([self.console, "locate", "--index", str(index), "--LLI", "0,0"], cwd=self.install_dir)
        self._adb_cmd(index, "emu geo fix 0 0")

    def GetPublicIP(self, index: int) -> str:
        raw = self._adb_cmd(index, "shell curl -s http://ip-api.com/json")
        try:
            data = json.loads(raw)
            return f"IP: {data.get('query')} | {data.get('city')}, {data.get('country')} | ISP: {data.get('isp')}"
        except Exception:
            return "មិនអាចទាញយក IP បានទេ (ពិនិត្យមើល Internet)"

    def InstallApp(self, index: int, apk_path: str) -> bool:
        if not os.path.isfile(apk_path):
            return False
        subprocess.run(
            [self.console, "installapp", "--index", str(index), "--filename", apk_path],
            cwd=self.install_dir, capture_output=True, text=True
        )
        return True

    def ListApps(self, index: int) -> list[str]:
        raw = self._adb_cmd(index, "shell pm list packages -3")
        return [p.replace("package:", "").strip() for p in raw.splitlines() if p.strip()]

    def PullApkToPc(self, index: int, package_name: str, save_dir: str) -> bool:
        os.makedirs(save_dir, exist_ok=True)
        path_res = self._adb_cmd(index, f"shell pm path {package_name}")
        apk_remote_path = ""
        for line in path_res.splitlines():
            if "package:" in line:
                apk_remote_path = line.replace("package:", "").strip()
                break

        if not apk_remote_path:
            return False

        save_file = os.path.join(save_dir, f"{package_name}.apk")
        subprocess.run(
            [self.console, "adb", "--index", str(index), "--command", f"pull {apk_remote_path} \"{save_file}\""],
            cwd=self.install_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        return os.path.isfile(save_file)


# =====================================================================
# Worker Thread (ការពារកុំឱ្យ GUI Freeze)
# =====================================================================
class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, task_func, *args):
        super().__init__()
        self.task_func = task_func
        self.args = args

    def run(self):
        try:
            self.task_func(self.log_signal.emit, *self.args)
        except Exception as e:
            self.log_signal.emit(f"❌ កំហុសបច្ចេកទេស: {e}")
        self.finished_signal.emit()


# =====================================================================
# Main GUI Window (PyQt5)
# =====================================================================
class LDPlayerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # ១. ផ្ទុកបញ្ជីដែលធ្លាប់បានបញ្ចូលពីមុន (បើគ្មានទេ គឺទទេស្អាត)
        self.paths_list = self.load_saved_paths()
        
        # ២. មិនដាក់ Path លំនាំដើមឡើយ (ទាល់តែមាន Path ទើប engine ស្គាល់)
        init_path = self.paths_list[0] if self.paths_list else ""
        self.launcher = LDPlayerLauncher(init_path)

        self.initUI()
        self.refresh_table()

    def load_saved_paths(self) -> list:
        """ផ្ទុកតែ Paths ដែលអ្នកប្រើប្រាស់ធ្លាប់បាន Add ប៉ុណ្ណោះ គ្មាន default ទេ"""
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # ច្រោះយកតែ Folder ណាដែលមានឯកសារ console ពិតប្រាកដ
                        valid_paths = [
                            p for p in data 
                            if os.path.isdir(p) and (
                                os.path.isfile(os.path.join(p, "ldconsole.exe")) or 
                                os.path.isfile(os.path.join(p, "dnconsole.exe"))
                            )
                        ]
                        return valid_paths
            except Exception:
                pass
        return []

    def save_paths(self):
        """រក្សាទុកបញ្ជី Paths ចូលក្នុង JSON"""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.paths_list, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"បរាជ័យក្នុងការ Save Config: {e}")

    def initUI(self):
        self.setWindowTitle("LDPlayer 9 Controller Dashboard (PyQt5)")
        self.resize(1180, 780)

        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e24; }
            QLabel { color: #f0f0f5; font-size: 13px; font-weight: bold; }
            QGroupBox { 
                color: #00d2d3; font-weight: bold; border: 1px solid #3d3d4e; 
                border-radius: 8px; margin-top: 10px; padding: 10px; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLineEdit, QComboBox { 
                background-color: #2b2b36; border: 1px solid #4a4a5a; 
                border-radius: 5px; color: #ffffff; padding: 6px; font-size: 13px;
            }
            QPushButton { 
                background-color: #0984e3; color: white; border-radius: 5px; 
                padding: 7px 12px; font-weight: bold; font-size: 12px;
            }
            QPushButton:hover { background-color: #74b9ff; }
            QPushButton:pressed { background-color: #0984e3; }
            QTableWidget { 
                background-color: #2b2b36; border: 1px solid #3d3d4e; 
                border-radius: 6px; color: #ffffff; gridline-color: #3d3d4e;
            }
            QTableWidget::item:selected {
                background-color: #0984e3; color: white;
            }
            QHeaderView::section { 
                background-color: #182C61; color: white; padding: 6px; font-weight: bold; 
            }
            QTextEdit { 
                background-color: #121217; color: #00ff7f; font-family: Consolas; 
                border: 1px solid #3d3d4e; border-radius: 6px; font-size: 12px;
            }
            QMenu {
                background-color: #2b2b36; border: 1px solid #4a4a5a; border-radius: 6px; color: #ffffff;
            }
            QMenu::item {
                padding: 7px 22px; font-weight: bold; font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #0984e3; color: #ffffff;
            }
            QMenu::separator {
                height: 1px; background: #3d3d4e; margin: 4px 8px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # =================================================================
        # ផ្នែកកំណត់ Path (ដំបូងឡើយគឺទទេស្អាត)
        # =================================================================
        box_path = QGroupBox("កំណត់ទីតាំង LDPlayer Directory (Path Selector)")
        box_path_layout = QHBoxLayout()

        lbl_path = QLabel("📁 LDPlayer Path:")
        self.combo_path = QComboBox()
        self.combo_path.addItems(self.paths_list)
        self.combo_path.currentTextChanged.connect(self.on_path_changed)

        btn_add_path = QPushButton("➕ Open & Add Path")
        btn_add_path.setStyleSheet("background-color: #00b894;")
        btn_add_path.clicked.connect(self.action_add_path)

        btn_del_path = QPushButton("🗑️ Remove Path")
        btn_del_path.setStyleSheet("background-color: #d63031;")
        btn_del_path.clicked.connect(self.action_remove_path)

        box_path_layout.addWidget(lbl_path)
        box_path_layout.addWidget(self.combo_path, stretch=3)
        box_path_layout.addWidget(btn_add_path)
        box_path_layout.addWidget(btn_del_path)
        box_path.setLayout(box_path_layout)
        main_layout.addWidget(box_path)

        # --- ផ្នែកតារាងបញ្ជីផ្ទាំង (Multi-Select & Right-Click) ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Index", "ឈ្មោះ (Name)", "ស្ថានភាព (Status)", "PID", "ADB Port"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        main_layout.addWidget(self.table, stretch=3)

        # --- ផ្ទាំងបញ្ជា (Control Panels) ---
        control_layout = QHBoxLayout()

        # ប្រអប់ទី ១៖ គ្រប់គ្រងផ្ទាំង និង Auto Move
        box_instance = QGroupBox("គ្រប់គ្រងផ្ទាំង & រៀបចំ (Instance & Move)")
        box_inst_layout = QVBoxLayout()
        
        create_h = QHBoxLayout()
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("ឈ្មោះផ្ទាំង ឧ. Bot_01")
        btn_create = QPushButton("➕ បង្កើត")
        btn_create.setStyleSheet("background-color: #00b894;")
        btn_create.clicked.connect(self.action_create)
        create_h.addWidget(self.input_name)
        create_h.addWidget(btn_create)
        box_inst_layout.addLayout(create_h)

        btn_row = QHBoxLayout()
        btn_start = QPushButton("▶️ បើក (Start Selected)")
        btn_start.clicked.connect(self.action_start)
        btn_stop = QPushButton("⏹️ បិទ (Stop Selected)")
        btn_stop.setStyleSheet("background-color: #e17055;")
        btn_stop.clicked.connect(self.action_stop)
        btn_del = QPushButton("🗑️ លុប")
        btn_del.setStyleSheet("background-color: #d63031;")
        btn_del.clicked.connect(self.action_delete)
        btn_row.addWidget(btn_start)
        btn_row.addWidget(btn_stop)
        btn_row.addWidget(btn_del)
        box_inst_layout.addLayout(btn_row)

        move_row = QHBoxLayout()
        btn_move = QPushButton("📐 Move Selected")
        btn_move.setStyleSheet("background-color: #0984e3;")
        btn_move.clicked.connect(self.action_move)

        btn_arrange_all = QPushButton("🗂️ Auto Arrange All")
        btn_arrange_all.setStyleSheet("background-color: #6c5ce7;")
        btn_arrange_all.clicked.connect(self.action_arrange_all)

        move_row.addWidget(btn_move)
        move_row.addWidget(btn_arrange_all)
        box_inst_layout.addLayout(move_row)

        btn_refresh = QPushButton("🔄 Refresh បញ្ជីផ្ទាំង")
        btn_refresh.clicked.connect(self.refresh_table)
        box_inst_layout.addWidget(btn_refresh)

        box_instance.setLayout(box_inst_layout)
        control_layout.addWidget(box_instance)

        # ប្រអប់ទី ២៖ GPS & Network
        box_tools = QGroupBox("GPS & Network")
        box_tools_layout = QVBoxLayout()

        gps_h = QHBoxLayout()
        self.combo_city = QComboBox()
        self.combo_city.addItems([
            "Phnom Penh", "Siem Reap", "Bangkok", "New York",
            "Los Angeles", "Miami", "Dallas", "Tokyo", "London"
        ])
        btn_gps = QPushButton("📍 Set GPS")
        btn_gps.clicked.connect(self.action_set_gps)
        btn_reset_gps = QPushButton("♻️ Reset")
        btn_reset_gps.setStyleSheet("background-color: #636e72;")
        btn_reset_gps.clicked.connect(self.action_reset_gps)
        gps_h.addWidget(self.combo_city)
        gps_h.addWidget(btn_gps)
        gps_h.addWidget(btn_reset_gps)
        box_tools_layout.addLayout(gps_h)

        btn_ip = QPushButton("🌐 ពិនិត្យមើល IP Public & ទីក្រុង")
        btn_ip.setStyleSheet("background-color: #6c5ce7;")
        btn_ip.clicked.connect(self.action_get_ip)
        box_tools_layout.addWidget(btn_ip)

        box_tools.setLayout(box_tools_layout)
        control_layout.addWidget(box_tools)

        # ប្រអប់ទី ៣៖ គ្រប់គ្រង APK
        box_apk = QGroupBox("គ្រប់គ្រង APK (APK Tools)")
        box_apk_layout = QVBoxLayout()

        btn_list_apk = QPushButton("📋 មើលបញ្ជី APK (Apps)")
        btn_list_apk.setStyleSheet("background-color: #8e44ad;")
        btn_list_apk.clicked.connect(self.action_list_apks)
        box_apk_layout.addWidget(btn_list_apk)

        btn_install_apk = QPushButton("📁 រើស File ដំឡើង (Install APK)")
        btn_install_apk.setStyleSheet("background-color: #16a085;")
        btn_install_apk.clicked.connect(self.action_install_apk)
        box_apk_layout.addWidget(btn_install_apk)

        dl_row = QHBoxLayout()
        btn_dl_all = QPushButton("💾 ទាញយកទាំងអស់")
        btn_dl_all.setStyleSheet("background-color: #d35400;")
        btn_dl_all.clicked.connect(self.action_download_all_apks)
        
        self.input_apk_no = QLineEdit()
        self.input_apk_no.setPlaceholderText("លេខរៀង ឧ. 1 ឬ 1, 2")
        btn_dl_num = QPushButton("📥 ទាញតាមលេខ")
        btn_dl_num.setStyleSheet("background-color: #27ae60;")
        btn_dl_num.clicked.connect(self.action_download_apk_by_num)
        
        dl_row.addWidget(btn_dl_all)
        dl_row.addWidget(self.input_apk_no)
        dl_row.addWidget(btn_dl_num)
        box_apk_layout.addLayout(dl_row)

        box_apk.setLayout(box_apk_layout)
        control_layout.addWidget(box_apk)

        main_layout.addLayout(control_layout)

        # --- ផ្នែកខាងក្រោម៖ Terminal Console Logs ---
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        main_layout.addWidget(self.log_view, stretch=2)

    # =====================================================================
    # មុខងារគ្រប់គ្រង LDPlayer Path (Add / Remove / Switch)
    # =====================================================================
    def action_add_path(self):
        """បើក Dialog ជ្រើសរើស Folder LDPlayer រួចផ្ទៀងផ្ទាត់ និងបន្ថែមចូល ComboBox"""
        folder = QFileDialog.getExistingDirectory(self, "ជ្រើសរើស Folder LDPlayer (កន្លែងមាន ldconsole.exe ឬ dnconsole.exe)")
        if not folder:
            return

        console1 = os.path.join(folder, "ldconsole.exe")
        console2 = os.path.join(folder, "dnconsole.exe")
        if not (os.path.isfile(console1) or os.path.isfile(console2)):
            QMessageBox.critical(
                self, "Path មិនត្រឹមត្រូវ",
                f"Folder នេះមិនមែនជា LDPlayer ទេ!\nរកមិនឃើញ 'ldconsole.exe' ឬ 'dnconsole.exe' ក្នុង:\n{folder}"
            )
            return

        folder = os.path.normpath(folder)
        if folder not in self.paths_list:
            self.paths_list.append(folder)
            self.combo_path.addItem(folder)
            self.combo_path.setCurrentText(folder)
            self.save_paths()
            self.log(f"✅ បានបន្ថែម និងទទួលស្គាល់ Path ថ្មី: {folder}")
        else:
            self.combo_path.setCurrentText(folder)
            self.log(f"ℹ️ Path នេះមានក្នុងបញ្ជីរួចហើយ: {folder}")

    def action_remove_path(self):
        """លុប Path ដែលកំពុងជ្រើសរើសចេញពី ComboBox និងបញ្ជី Save"""
        curr_path = self.combo_path.currentText().strip()
        if not curr_path:
            QMessageBox.warning(self, "ការដាស់តឿន", "គ្មាន Path ណាមួយត្រូវបានជ្រើសរើសឡើយ!")
            return

        reply = QMessageBox.question(
            self, "បញ្ជាក់ការលុប Path",
            f"តើអ្នកចង់លុប Path នេះចេញពីបញ្ជីមែនទេ?\n{curr_path}",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if curr_path in self.paths_list:
                self.paths_list.remove(curr_path)
                self.save_paths()

            idx = self.combo_path.findText(curr_path)
            if idx >= 0:
                self.combo_path.removeItem(idx)

            self.log(f"🗑️ បានលុប Path: {curr_path}")
            if self.combo_path.count() == 0:
                self.launcher.set_path("")
                self.refresh_table()

    def on_path_changed(self, new_path: str):
        """ផ្លាស់ប្តូរ Engine Path ពេល User ចុចរើស ឬបញ្ចូល Path ថ្មី"""
        self.launcher.set_path(new_path)
        if new_path:
            self.log(f"🔄 បានប្តូរទៅកាន់ LDPlayer Path: {new_path}")
        self.refresh_table()

    # =====================================================================
    # មុខងារជំនួយ និង UI Events
    # =====================================================================
    def log(self, message: str):
        self.log_view.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    def get_selected_indices(self) -> list[int]:
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "ការដាស់តឿន", "សូមចុច ឬអូសម៉ៅស៍ Highlight ជ្រើសរើសជួរក្នុងតារាងជាមុនសិន!")
            return []

        indices = []
        for row in sorted(selected_rows):
            idx_text = self.table.item(row, 0).text()
            if idx_text.isdigit():
                indices.append(int(idx_text))
        return indices

    def open_context_menu(self, position):
        if not self.launcher.is_valid():
            QMessageBox.warning(self, "ការដាស់តឿន", "សូម Add Path LDPlayer ជាមុនសិន!")
            return

        indices = self.get_selected_indices()
        if not indices:
            return

        menu = QMenu(self)

        act_start = QAction(f"▶️ បើកដំណើរការ (Start) ({len(indices)} ផ្ទាំង)", self)
        act_start.triggered.connect(self.action_start)
        menu.addAction(act_start)

        act_stop = QAction(f"⏹️ បិទដំណើរការ (Stop) ({len(indices)} ផ្ទាំង)", self)
        act_stop.triggered.connect(self.action_stop)
        menu.addAction(act_stop)

        act_move = QAction(f"📐 តម្រៀបទីតាំង (Move Selected)", self)
        act_move.triggered.connect(self.action_move)
        menu.addAction(act_move)

        menu.addSeparator()

        act_gps = QAction(f"📍 Set GPS ទៅកាន់ {self.combo_city.currentText()}", self)
        act_gps.triggered.connect(self.action_set_gps)
        menu.addAction(act_gps)

        act_ip = QAction("🌐 ពិនិត្យមើល IP Public & ទីក្រុង", self)
        act_ip.triggered.connect(self.action_get_ip)
        menu.addAction(act_ip)

        menu.addSeparator()

        act_list_apk = QAction("📋 មើលបញ្ជី APK", self)
        act_list_apk.triggered.connect(self.action_list_apks)
        menu.addAction(act_list_apk)

        act_install_apk = QAction("📁 ដំឡើង APK ចូល", self)
        act_install_apk.triggered.connect(self.action_install_apk)
        menu.addAction(act_install_apk)

        act_dl_apk = QAction("💾 ទាញយក APK ទាំងអស់មកកុំព្យូទ័រ", self)
        act_dl_apk.triggered.connect(self.action_download_all_apks)
        menu.addAction(act_dl_apk)

        menu.addSeparator()

        act_del = QAction("🗑️ លុបផ្ទាំង (Delete)", self)
        act_del.triggered.connect(self.action_delete)
        menu.addAction(act_del)

        menu.exec_(QCursor.pos())

    def refresh_table(self):
        # បើមិនទាន់កំណត់ Path ឬ Path មិនត្រឹមត្រូវ គឺមិនបង្ហាញទិន្នន័យឡើយ
        if not self.launcher.is_valid():
            self.table.setRowCount(0)
            self.log("⚠️ មិនទាន់ស្គាល់ LDPlayer ទេ! សូមចុច '➕ Open & Add Path' ដើម្បីជ្រើសរើស Folder ដំឡើងរបស់ LDPlayer។")
            return

        instances = self.launcher.List()
        self.table.setRowCount(len(instances))
        for row, inst in enumerate(instances):
            self.table.setItem(row, 0, QTableWidgetItem(str(inst["index"])))
            self.table.setItem(row, 1, QTableWidgetItem(inst["name"]))
            
            status_item = QTableWidgetItem("🟢 Running" if inst["running"] else "🔴 Stopped")
            status_item.setForeground(QColor("#00ff7f") if inst["running"] else QColor("#ff7675"))
            self.table.setItem(row, 2, status_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(str(inst["pid"])))
            self.table.setItem(row, 4, QTableWidgetItem(inst["adb_port"]))

    def run_worker(self, func, *args):
        if not self.launcher.is_valid():
            QMessageBox.critical(self, "កំហុស", "មិនទាន់មាន LDPlayer Path ត្រឹមត្រូវទេ! សូមចុច '➕ Open & Add Path' ជាមុនសិន។")
            return
        self.worker = WorkerThread(func, *args)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.refresh_table)
        self.worker.start()

    # =====================================================================
    # Actions បញ្ជាទៅកាន់ LDPlayer
    # =====================================================================
    def action_create(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "ខ្វះទិន្នន័យ", "សូមវាយបញ្ចូលឈ្មោះផ្ទាំង!")
            return
        
        def task(log):
            log(f"កំពុងបង្កើតផ្ទាំងថ្មី '{name}' ទំហំ 250x500...")
            idx = self.launcher.Create(name)
            log(f"✅ បានបង្កើតផ្ទាំង '{name}' [Index: {idx}] រួចរាល់!")
        
        self.input_name.clear()
        self.run_worker(task)

    def action_start(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            log(f"កំពុងបើកដំណើរការផ្ទាំងដែលបានជ្រើសរើស: {indices}...")
            for idx in indices:
                log(f"-> កំពុង Launch ផ្ទាំង [{idx}]...")
                self.launcher.Start(idx)

            log("⏳ កំពុងរង់ចាំ ៤ វិនាទីដើម្បីឱ្យផ្ទាំងមានលំនឹង...")
            time.sleep(4)

            log(f"📐 កំពុងតម្រៀបទីតាំងផ្ទាំង {indices} ឡើងវិញ...")
            for idx in indices:
                self.launcher.Move(idx)

            log(f"✅ ផ្ទាំងទាំងអស់ {indices} បានបើក និងរៀបចំទីតាំងចប់សព្វគ្រប់!")
        self.run_worker(task)

    def action_stop(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            log(f"កំពុងបិទផ្ទាំង: {indices}...")
            for idx in indices:
                self.launcher.Stop(idx)
                log(f"-> បានបិទផ្ទាំង [{idx}]")
            log(f"✅ បានបិទគ្រប់ផ្ទាំងដែលជ្រើសរើសរួចរាល់!")
        self.run_worker(task)

    def action_delete(self):
        indices = self.get_selected_indices()
        if not indices: return
        reply = QMessageBox.question(
            self, "បញ្ជាក់ការលុប", f"តើអ្នកពិតជាចង់លុបផ្ទាំងទាំងនេះ {indices} មែនទេ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            def task(log):
                for idx in indices:
                    log(f"កំពុងលុបផ្ទាំង [{idx}]...")
                    self.launcher.Delete(idx)
                log(f"✅ បានលុបផ្ទាំង {indices} ចេញពីប្រព័ន្ធ!")
            self.run_worker(task)

    def action_move(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            log(f"កំពុងតម្រៀបទីតាំងផ្ទាំង: {indices}...")
            for idx in indices:
                self.launcher.Move(idx)
            log(f"✅ បានតម្រៀបទីតាំងផ្ទាំង {indices} រួចរាល់!")
        self.run_worker(task)

    def action_arrange_all(self):
        def task(log):
            log("កំពុងរៀបចំតម្រៀបគ្រប់ផ្ទាំងដែលកំពុងបើកដំណើរការ (Auto Arrange All)...")
            self.launcher.ArrangeAll()
            log("✅ បានតម្រៀបគ្រប់ផ្ទាំងទាំងអស់ចប់សព្វគ្រប់!")
        self.run_worker(task)

    def action_set_gps(self):
        indices = self.get_selected_indices()
        if not indices: return
        city = self.combo_city.currentText()
        def task(log):
            for idx in indices:
                log(f"កំពុងកំណត់ GPS លើផ្ទាំង [{idx}] ទៅកាន់ {city}...")
                self.launcher.SetGPS(idx, city)
            log(f"✅ បានកំណត់ GPS ទៅកាន់ {city} លើផ្ទាំង {indices} រួចរាល់!")
        self.run_worker(task)

    def action_reset_gps(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            for idx in indices:
                log(f"កំពុងដោះ GPS លើផ្ទាំង [{idx}]...")
                self.launcher.ResetGPS(idx)
            log(f"✅ បានដោះ GPS លើផ្ទាំង {indices} រួចរាល់!")
        self.run_worker(task)

    def action_get_ip(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            for idx in indices:
                info = self.launcher.GetPublicIP(idx)
                log(f"🌐 [Index {idx}] {info}")
        self.run_worker(task)

    def action_list_apks(self):
        indices = self.get_selected_indices()
        if not indices: return
        def task(log):
            for idx in indices:
                apks = self.launcher.ListApps(idx)
                log(f"=== បញ្ជី APK លើផ្ទាំង [{idx}] ({len(apks)} apps) ===")
                for i, a in enumerate(apks, 1):
                    log(f"  [{i}] -> {a}")
        self.run_worker(task)

    def action_install_apk(self):
        indices = self.get_selected_indices()
        if not indices: return

        apk_path, _ = QFileDialog.getOpenFileName(
            self, "ជ្រើសរើសឯកសារ APK ដើម្បីដំឡើង", "", "APK Files (*.apk)"
        )
        if not apk_path:
            return

        def task(log):
            for idx in indices:
                log(f"កំពុងដំឡើង APK ចូលក្នុងផ្ទាំង [{idx}]...")
                self.launcher.InstallApp(idx, apk_path)
            log(f"✅ បានដំឡើង APK លើគ្រប់ផ្ទាំងដែលជ្រើសរើសរួចរាល់!")

        self.run_worker(task)

    def action_download_all_apks(self):
        indices = self.get_selected_indices()
        if not indices: return

        save_folder = QFileDialog.getExistingDirectory(self, "ជ្រើសរើស Folder សម្រាប់រក្សាទុក APK", r"C:\LDPlayer_APKs")
        if not save_folder:
            return

        def task(log):
            for idx in indices:
                target_dir = os.path.join(save_folder, f"instance_{idx}")
                log(f"កំពុងទាញយក APK ផ្ទាំង [{idx}] ទៅកាន់: {target_dir}...")
                apks = self.launcher.ListApps(idx)
                for a in apks:
                    self.launcher.PullApkToPc(idx, a, target_dir)
            log(f"✅ បានទាញយក APK ទាំងអស់ចប់សព្វគ្រប់!")

        self.run_worker(task)

    def action_download_apk_by_num(self):
        indices = self.get_selected_indices()
        if not indices: return

        num_text = self.input_apk_no.text().strip()
        if not num_text:
            QMessageBox.warning(self, "ខ្វះទិន្នន័យ", "សូមវាយបញ្ចូលលេខរៀង APK (ឧ. 1 ឬ 1, 2)!")
            return

        save_folder = QFileDialog.getExistingDirectory(self, "ជ្រើសរើស Folder សម្រាប់រក្សាទុក APK", r"C:\LDPlayer_APKs")
        if not save_folder:
            return

        def task(log):
            nums = [int(p) for p in num_text.replace(" ", "").split(",") if p.isdigit()]
            for idx in indices:
                apks = self.launcher.ListApps(idx)
                target_dir = os.path.join(save_folder, f"instance_{idx}")
                for num in nums:
                    idx_in_list = num - 1
                    if 0 <= idx_in_list < len(apks):
                        chosen_app = apks[idx_in_list]
                        log(f"-> [Index {idx}] កំពុងទាញយកលេខ [{num}]: {chosen_app}...")
                        self.launcher.PullApkToPc(idx, chosen_app, target_dir)
            log(f"✅ ការទាញយកតាមលេខរៀងបានបញ្ចប់!")

        self.input_apk_no.clear()
        self.run_worker(task)


# =====================================================================
# ចាប់ផ្តើមដំណើរការកម្មវិធី
# =====================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LDPlayerGUI()
    window.show()
    sys.exit(app.exec_())
