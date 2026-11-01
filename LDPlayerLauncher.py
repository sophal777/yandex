
import os
import subprocess
import time
import ctypes
import random
import json
from ctypes import wintypes
from typing import Optional, Tuple, Dict, Any

user32 = ctypes.windll.user32


class LDPlayerLauncher:
    def __init__(self, install_dir: str = r"D:\leidian\LDPlayer9"):
        """កំណត់ទីតាំងដំឡើងរបស់ LDPlayer"""
        self.install_dir = install_dir
        self.console = os.path.join(install_dir, "ldconsole.exe")
        
        if not os.path.isfile(self.console):
            self.console = os.path.join(install_dir, "dnconsole.exe")
            if not os.path.isfile(self.console):
                raise FileNotFoundError(f"រកមិនឃើញ console ក្នុង: {install_dir}")

    # ==========================================================
    # ជំនួយការ ADB, ម៉ូឌែល និងព័ត៌មានប្រព័ន្ធ
    # ==========================================================
    def _adb_cmd(self, index: int, command: str) -> str:
        res = subprocess.run(
            [self.console, "adb", "--index", str(index), "--command", command],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        return res.stdout.strip()

    def _get_version(self) -> str:
        v_paths = [
            os.path.join(self.install_dir, "vms", "version.txt"),
            os.path.join(self.install_dir, "version.txt"),
        ]
        for vp in v_paths:
            if os.path.isfile(vp):
                try:
                    with open(vp, "r", encoding="utf-8") as f:
                        val = f.read().strip()
                        if val:
                            return val
                except Exception:
                    pass
        return "9.0 (LDPlayer 9)"

    def _get_cpu_cores(self, index: int) -> str:
        raw = self._adb_cmd(index, "shell cat /proc/cpuinfo")
        cores = sum(1 for line in raw.splitlines() if line.strip().startswith("processor"))
        return f"{cores} cores" if cores > 0 else "Unknown"

    def _get_random_device(self) -> Tuple[str, str]:
        devices = [
            ("samsung", "SM-S928B"),       # Galaxy S24 Ultra
            ("samsung", "SM-S918B"),       # Galaxy S23 Ultra
            ("samsung", "SM-F946B"),       # Galaxy Z Fold 5
            ("XIAOMI", "23127PN0CC"),      # Xiaomi 14 Pro
            ("XIAOMI", "2509FPN0BC"),      # Xiaomi Custom
            ("Redmi", "Redmi Note 13 Pro+"),
            ("Google", "Pixel 9 Pro XL"),
            ("Google", "Pixel 8 Pro"),
            ("OnePlus", "CPH2581"),        # OnePlus 12
            ("OPPO", "CPH2505"),           # Find X7 Ultra
            ("vivo", "V2324A"),            # Vivo X100 Pro
            ("asus", "ASUS_AI2401")        # ROG Phone 8
        ]
        return random.choice(devices)

    def _get_window_size(self, hwnd: int) -> Tuple[int, int]:
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        return (rect.right - rect.left), (rect.bottom - rect.top)

    def _resolve_targets(self, target: int | list[int] | str) -> list[int]:
        if isinstance(target, str) and target.lower() == "all":
            running_list = [inst["index"] for inst in self.List(print_output=False) if inst["running"]]
            if not running_list:
                print("គ្មានផ្ទាំងណាមួយកំពុងបើកដំណើរការឡើយ!")
            return running_list
        elif isinstance(target, int):
            return [target]
        elif isinstance(target, list):
            return target
        return []

    # ==========================================================
    # មុខងារគ្រប់គ្រងផ្ទាំង (Instance Management)
    # ==========================================================
    def List(self, print_output: bool = True) -> list[dict]:
        """[១] បង្ហាញ និងទាញយកបញ្ជីផ្ទាំងទាំងអស់ និងស្ថានភាពដំណើរការ"""
        proc = subprocess.run(
            [self.console, "list2"],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        instances = []
        if print_output:
            print("\n=== បញ្ជីផ្ទាំង LDPlayer ទាំងអស់ ===")
        for line in proc.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    idx = int(parts[0])
                    name = parts[1]
                    is_running = len(parts) >= 3 and int(parts[2]) > 0
                    instances.append({"index": idx, "name": name, "running": is_running})
                    if print_output:
                        status = "🟢 កំពុងបើក (Running)" if is_running else "🔴 បានបិទ (Stopped)"
                        print(f"[{idx}] {name:<15} -> {status}")
                except ValueError:
                    pass
        if print_output:
            print("===================================\n")
        return instances

    def GetIndex(self, name: str) -> Optional[int]:
        """[២] ស្វែងរកលេខរៀង Index តាមរយៈឈ្មោះផ្ទាំង"""
        proc = subprocess.run(
            [self.console, "list2"],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        for line in proc.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and parts[1] == name:
                try:
                    return int(parts[0])
                except ValueError:
                    pass
        return None

    def Create(
        self,
        name: str = "Bot_01",
        cpu: int = 2,
        memory: int = 2048,
        resolution: str = "250,500,100",
        manufacturer: str = "random",
        model: str = "random"
    ) -> int:
        """[៣] បង្កើតផ្ទាំងថ្មី (CPU 2, RAM 2048, Res 250x500 DPI 100, Random Device Profile)"""
        existing = self.GetIndex(name)
        if existing is not None:
            print(f"ឈ្មោះ '{name}' មានរួចហើយ [Index: {existing}]")
            return existing

        if manufacturer.lower() == "random" or model.lower() == "random":
            rand_manu, rand_model = self._get_random_device()
            manufacturer = rand_manu if manufacturer.lower() == "random" else manufacturer
            model = rand_model if model.lower() == "random" else model

        print(f"កំពុងបង្កើតផ្ទាំងថ្មីឈ្មោះ: '{name}'...")
        subprocess.run([self.console, "add", "--name", name], cwd=self.install_dir, capture_output=True, text=True)

        new_idx = self.GetIndex(name)
        if new_idx is None:
            new_idx = 0

        print(f"កំពុងកំណត់ទំហំ {resolution} និង Device: {manufacturer} ({model})...")
        subprocess.run(
            [
                self.console, "modify", "--index", str(new_idx),
                "--cpu", str(cpu),
                "--memory", str(memory),
                "--resolution", resolution,
                "--manufacturer", manufacturer,
                "--model", model
            ],
            cwd=self.install_dir,
            capture_output=True,
            text=True
        )
        print(f"បានបង្កើត '{name}' [Index: {new_idx}] រួចរាល់!\n")
        return new_idx

    def Move(self, index: int = 0, start_x: int = 0, start_y: int = 0, timeout: int = 15) -> bool:
        """[៤] រៀបចំផ្ទាំងលើកុំព្យូទ័រមិនឱ្យជាន់គ្នាស្វ័យប្រវត្តិតាម Windows API"""
        start_time = time.time()
        target_hwnd = None
        running_indices = []

        while time.time() - start_time < timeout:
            proc = subprocess.run(
                [self.console, "list2"], cwd=self.install_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            running_indices = []
            for line in proc.stdout.splitlines():
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    try:
                        curr_idx = int(parts[0])
                        top_handle = int(parts[2])
                        if top_handle > 0:
                            running_indices.append(curr_idx)
                            if curr_idx == index:
                                target_hwnd = top_handle
                    except ValueError:
                        pass
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
        print(f"-> ផ្ទាំង [{index}] រៀបចំនៅ X={final_x}, Y={final_y}")
        return True

    def Wait(self, index: int = 0, timeout: int = 60) -> bool:
        """[៥] រង់ចាំឱ្យ Android Boot ចប់សព្វគ្រប់ ១០០%"""
        print(f"កំពុងរង់ចាំផ្ទាំងលេខ [{index}] បើកចប់សព្វគ្រប់...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            proc = subprocess.run(
                [self.console, "adb", "--index", str(index), "--command", "shell getprop sys.boot_completed"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            if "1" in proc.stdout:
                print(f"ផ្ទាំងលេខ [{index}] បើកជោគជ័យ ១០០% ហើយ!")
                return True
            time.sleep(2)
        print(f"ផ្ទាំងលេខ [{index}] ផុតកំណត់ពេល (Timeout)!")
        return False

    def Start(self, target: int | list[int], start_x: int = 0, start_y: int = 0, auto_wait: bool = True) -> None:
        """[៦] បើកផ្ទាំងតែមួយ ឬច្រើនផ្ទាំងដំណាលគ្នា ព្រមទាំងតម្រៀបកុំឱ្យស្ទួនគ្នា"""
        instances = [target] if isinstance(target, int) else target
        for idx in instances:
            print(f"កំពុងបើកដំណើរការ LDPlayer ផ្ទាំងលេខ [{idx}]...")
            subprocess.run([self.console, "launch", "--index", str(idx)], cwd=self.install_dir)
            self.Move(index=idx, start_x=start_x, start_y=start_y)

        if auto_wait:
            print("\n--- កំពុងរង់ចាំគ្រប់ផ្ទាំង Boot ចប់ ---")
            for idx in instances:
                self.Wait(idx)

    def Stop(self, index: int = 0) -> None:
        """[៧] បិទផ្ទាំង LDPlayer"""
        subprocess.run([self.console, "quit", "--index", str(index)], cwd=self.install_dir)
        print(f"បានបិទផ្ទាំងលេខ [{index}] រួចរាល់!")

    def Delete(self, target: int | str) -> bool:
        """[៨] លុបផ្ទាំងចេញពី LDPlayer (តាមរយៈ Index ឬតាមឈ្មោះ)"""
        if isinstance(target, str):
            idx = self.GetIndex(target)
            if idx is None:
                print(f"រកមិនឃើញផ្ទាំងឈ្មោះ '{target}' ដើម្បីលុបទេ!")
                return False
        else:
            idx = target

        self.Stop(idx)
        time.sleep(1)

        print(f"កំពុងលុបផ្ទាំងលេខ [Index: {idx}]...")
        subprocess.run(
            [self.console, "remove", "--index", str(idx)],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        print(f"បានលុបផ្ទាំង [Index: {idx}] រួចរាល់!")
        return True

    def ShowAllInfo(self, index: int = 0) -> None:
        """[៩] បង្ហាញព័ត៌មានផ្ទាំងពេញលេញ (ADB Port បង្ហាញទាំងពេលបិទ និងបើក)"""
        proc = subprocess.run(
            [self.console, "list2"], cwd=self.install_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore"
        )
        name, is_running, pid, top_hwnd = "Unknown", False, 0, 0
        for line in proc.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and parts[0] == str(index):
                name = parts[1]
                if len(parts) >= 6:
                    top_hwnd = int(parts[2]) if parts[2].isdigit() else 0
                    is_running = int(parts[4]) == 1 if parts[4].isdigit() else False
                    pid = int(parts[5]) if parts[5].isdigit() else 0
                break

        print("\n===== ព័ត៌មានផ្ទាំង LDPlayer =====")
        print(f"LDPlayer path     : {self.install_dir}")
        print(f"LDPlayer version  : {self._get_version()}")
        print(f"Multi-instance    : No.{index} ({name})")
        print(f"Running Status    : {'🟢 កំពុងបើក (Running)' if is_running else '🔴 បានបិទ (Stopped)'}")
        print(f"ADB debug port    : emulator-{5554 + index * 2}")

        if is_running:
            manu = self._adb_cmd(index, "shell getprop ro.product.manufacturer")
            model = self._adb_cmd(index, "shell getprop ro.product.model")
            
            # RAM
            ram_val = "Unknown"
            mem_info = self._adb_cmd(index, "shell cat /proc/meminfo")
            for m_line in mem_info.splitlines():
                if "MemTotal:" in m_line:
                    kb = "".join(filter(str.isdigit, m_line))
                    if kb:
                        ram_val = f"{round(int(kb) / 1024)}M"
                    break

            # Res & DPI
            res_val = self._adb_cmd(index, "shell wm size").replace("Physical size:", "").strip()
            dpi_val = self._adb_cmd(index, "shell wm density").replace("Physical density:", "").strip()

            print(f"Process PID       : {pid}")
            print(f"Window Handle     : {top_hwnd}")
            print(f"CPU               : {self._get_cpu_cores(index)}")
            print(f"RAM               : {ram_val}")
            print(f"Resolution        : {res_val}")
            print(f"DPI               : {dpi_val}")
            print(f"Model Device      : {manu} ({model})")
            
            pm_list = self._adb_cmd(index, "shell pm list packages -3")
            installed = [p.replace("package:", "").strip() for p in pm_list.splitlines() if p.strip()]
            apk_count = len(installed)
            apk_str = ", ".join(installed[:5]) + ("..." if apk_count > 5 else "")
            print(f"APK ({apk_count} apps)      : {apk_str if apk_count > 0 else 'គ្មាន APK បន្ថែម'}")
        else:
            print("*(ផ្ទាំងនេះមិនទាន់បើកដំណើរការទេ - ព័ត៌មាន Hardware/Android នឹងបង្ហាញពេលបើក)*")
        print("==================================\n")

    # ==========================================================
    # មុខងារគ្រប់គ្រង APK
    # ==========================================================
    def ListApps(self, index: int = 0) -> list[str]:
        """[១០] ពិនិត្យមើលតែបញ្ជី APK ជាមួយលេខរៀង [1], [2]..."""
        raw = self._adb_cmd(index, "shell pm list packages -3")
        apps = [line.replace("package:", "").strip() for line in raw.splitlines() if line.strip()]

        print(f"\n=== បញ្ជី APK លើផ្ទាំង [Index: {index}] (សរុប {len(apps)} apps) ===")
        if not apps:
            print("គ្មាន APK បន្ថែម (Third-party App) ត្រូវបានដំឡើងឡើយ!")
        else:
            for num, app in enumerate(apps, start=1):
                print(f"លេខរៀង [{num}] -> {app}")
        print("===================================================\n")
        return apps

    def _pull_apk_to_pc(self, index: int, package_name: str, save_dir: str) -> bool:
        os.makedirs(save_dir, exist_ok=True)
        path_res = self._adb_cmd(index, f"shell pm path {package_name}")
        apk_remote_path = ""
        for line in path_res.splitlines():
            if "package:" in line:
                apk_remote_path = line.replace("package:", "").strip()
                break

        if not apk_remote_path:
            print(f"រកមិនឃើញទីតាំង APK របស់ '{package_name}' ទេ!")
            return False

        save_file = os.path.join(save_dir, f"{package_name}.apk")
        print(f"កំពុងទាញយក '{package_name}' មកកាន់: {save_file}...")

        subprocess.run(
            [self.console, "adb", "--index", str(index), "--command", f"pull {apk_remote_path} \"{save_file}\""],
            cwd=self.install_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        if os.path.isfile(save_file):
            print(f"ទាញយកជោគជ័យ: {save_file}")
            return True
        return False

    def DownloadAllApks(self, index: int = 0, save_dir: str = r"C:\LDPlayer_APKs") -> None:
        """[១១] ទាញយក (Download) APK ទាំងអស់មកដាក់លើកុំព្យូទ័រ"""
        apps = self.ListApps(index)
        if not apps:
            print("គ្មាន APK សម្រាប់ទាញយកទេ!")
            return

        target_folder = os.path.join(save_dir, f"instance_{index}")
        print(f"ចាប់ផ្តើមទាញយក APK ទាំងអស់ ({len(apps)} apps) ទៅកាន់: {target_folder}\n")

        for app in apps:
            self._pull_apk_to_pc(index, app, target_folder)

        print(f"\nបានទាញយក APK ទាំងអស់ចប់សព្វគ្រប់!")

    def DownloadApkByNumbers(self, index: int = 0, numbers: int | list[int] = 1, save_dir: str = r"C:\LDPlayer_APKs") -> None:
        """[១២] កំណត់ទាញយកតែ APK ណាខ្លះតាមលេខរៀង (ឧ. លេខ 1 ឬ [1, 3])"""
        apps = self.ListApps(index)
        if not apps:
            return

        selected_nums = [numbers] if isinstance(numbers, int) else numbers
        target_folder = os.path.join(save_dir, f"instance_{index}")

        for num in selected_nums:
            idx_in_list = num - 1
            if 0 <= idx_in_list < len(apps):
                selected_app = apps[idx_in_list]
                print(f"\nជ្រើសរើសលេខរៀង [{num}]: {selected_app}")
                self._pull_apk_to_pc(index, selected_app, target_folder)
            else:
                print(f"លេខរៀង [{num}] មិនត្រឹមត្រូវទេ! (មានត្រឹមលេខ 1 ដល់ {len(apps)})")

    # ==========================================================
    # មុខងារ IP Public និង GPS
    # ==========================================================
    def GetPublicIP(self, index: int = 0) -> Dict[str, Any]:
        """[១៣] ពិនិត្យមើល IP Public, City, Country និង ISP លើផ្ទាំង LDPlayer"""
        print(f"កំពុងពិនិត្យមើល IP Public លើផ្ទាំង [{index}]...")
        raw_json = self._adb_cmd(index, "shell curl -s http://ip-api.com/json")
        
        data = {
            "ip": "Unknown",
            "city": "Unknown",
            "region": "Unknown",
            "country": "Unknown",
            "isp": "Unknown",
            "org": "Unknown"
        }

        try:
            if "query" in raw_json:
                res = json.loads(raw_json)
                data["ip"] = res.get("query", "Unknown")
                data["city"] = res.get("city", "Unknown")
                data["region"] = res.get("regionName", "Unknown")
                data["country"] = res.get("country", "Unknown")
                data["isp"] = res.get("isp", "Unknown")
                data["org"] = res.get("org", "Unknown")
            else:
                ip_only = self._adb_cmd(index, "shell curl -s https://api.ipify.org")
                if ip_only and not "not found" in ip_only:
                    data["ip"] = ip_only.strip()
        except Exception as e:
            print(f"មានបញ្ហាក្នុងការទាញទិន្នន័យ IP: {e}")

        print(f"\n===== ព័ត៌មាន IP PUBLIC [Index: {index}] =====")
        print(f"* IP Address : {data['ip']}")
        print(f"* ទីក្រុង (City) : {data['city']}")
        print(f"* ខេត្ត/តំបន់  : {data['region']}")
        print(f"* ប្រទេស     : {data['country']}")
        print(f"* ISP        : {data['isp']} ({data['org']})")
        print("============================================\n")

        return data

    def SetGPS(
        self,
        target: int | list[int] | str = "all",
        location: str | float = "Phnom Penh",
        lng: Optional[float] = None
    ) -> bool:
        """កំណត់ទីតាំង GPS (ផ្ទាំងទោល, បញ្ជីផ្ទាំង, ឬ ទាំងអស់ "all" ជាមួយ City USA & Global)"""
        city_db = {
            # USA
            "los angeles": (34.0522, -118.2437),
            "san francisco": (37.7749, -122.4194),
            "san diego": (32.7157, -117.1611),
            "new york": (40.7128, -74.0060),
            "boston": (42.3601, -71.0589),
            "washington dc": (38.9072, -77.0369),
            "houston": (29.7604, -95.3698),
            "dallas": (32.7767, -96.7970),
            "austin": (30.2672, -97.7431),
            "miami": (25.7617, -80.1918),
            "orlando": (28.5383, -81.3792),
            "chicago": (41.8781, -87.6298),
            "seattle": (47.6062, -122.3321),
            "las vegas": (36.1699, -115.1398),
            # កម្ពុជា & អាស៊ី
            "phnom penh": (11.5564, 104.9282),
            "siem reap": (13.3671, 103.8448),
            "bangkok": (13.7563, 100.5018),
            "tokyo": (35.6762, 139.6503),
            "singapore": (1.3521, 103.8198),
            "london": (51.5074, -0.1278),
        }

        if isinstance(location, str):
            city_key = location.strip().lower()
            if city_key in city_db:
                target_lat, target_lng = city_db[city_key]
                loc_display = f"ទីក្រុង '{location.title()}'"
            else:
                print(f"រកមិនឃើញទីក្រុង '{location}' ទេ! (ប្រើលំនាំដើម: Phnom Penh)")
                target_lat, target_lng = city_db["phnom penh"]
                loc_display = "Phnom Penh (Default)"
        else:
            target_lat = float(location)
            target_lng = float(lng) if lng is not None else 104.9282
            loc_display = f"កូអរដោនេ ({target_lat}, {target_lng})"

        indices = self._resolve_targets(target)
        if not indices:
            return False

        print(f"\n--- កំពុងកំណត់ GPS ទៅកាន់: {loc_display} [Lat={target_lat}, Lng={target_lng}] ---")
        for idx in indices:
            subprocess.run(
                [self.console, "locate", "--index", str(idx), "--LLI", f"{target_lng},{target_lat}"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            self._adb_cmd(idx, f"emu geo fix {target_lng} {target_lat}")
            print(f"-> បានកំណត់ GPS លើផ្ទាំង [{idx}] រួចរាល់")

        print("------------------------------------------------------------------\n")
        return True

    def ResetGPS(self, target: int | list[int] | str = "all") -> bool:
        """ដោះទីតាំង GPS ចេញ (ត្រឡប់ទៅ 0, 0 វិញ)"""
        indices = self._resolve_targets(target)
        if not indices:
            return False

        print("\n--- កំពុងដោះទីតាំង GPS ចេញ (Reset to 0,0) ---")
        for idx in indices:
            subprocess.run(
                [self.console, "locate", "--index", str(idx), "--LLI", "0,0"],
                cwd=self.install_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore"
            )
            self._adb_cmd(idx, "emu geo fix 0 0")
            print(f"-> បានដោះទីតាំង GPS លើផ្ទាំង [{idx}] រួចរាល់")

        print("-------------------------------------------\n")
        return True
if __name__ == "__main__":
    kh = LDPlayerLauncher()

    # ==========================================================
    # [លេខ ១] មើលបញ្ជីផ្ទាំងទាំងអស់ និងស្ថានភាព (បើក ឬ បិទ)
    # ==========================================================
    kh.List()

    # ==========================================================
    # [លេខ ២] ស្វែងរកលេខ Index តាមរយៈឈ្មោះផ្ទាំង
    # ==========================================================
    my_idx = kh.GetIndex("Bot_02")
    print(f"Index របស់ Bot_02 គឺ: {my_idx}")

    # ==========================================================
    # [លេខ ៣] បង្កើតផ្ទាំងថ្មី (Res 250x500, CPU 2, RAM 2048, Random Model)
    # ==========================================================
    bot_idx = kh.Create("Bot_03")

    # ==========================================================
    # [លេខ ៤] រៀបចំផ្ទាំងលើអេក្រង់មិនឱ្យជាន់គ្នា (Auto Grid Arrangement)
    # ==========================================================
    kh.Move(index=bot_idx, start_x=0, start_y=0)

    # ==========================================================
    # [លេខ ៥] រង់ចាំផ្ទាំង Boot ឱ្យចប់សព្វគ្រប់ ១០០%
    # ==========================================================
    kh.Wait(index=bot_idx, timeout=60)

    # ==========================================================
    # [លេខ ៦] បើកដំណើរការផ្ទាំង (ទោល ឬ បើកច្រើនដំណាលគ្នា)
    # ==========================================================
    # បើកផ្ទាំងតែមួយ៖
    # kh.Start(bot_idx)

    # ឬបើកច្រើនផ្ទាំងដំណាលគ្នា៖
    # kh.Start([0, 11])

    # ==========================================================
    # [លេខ ៧] បិទផ្ទាំងដំណើរការ
    # ==========================================================
    # kh.Stop(bot_idx)

    # ==========================================================
    # [លេខ ៨] លុបផ្ទាំងចោល (Delete by Index or Name)
    # ==========================================================
    # kh.Delete(bot_idx)      # លុបតាម Index
    # kh.Delete("Bot_03")    # ឬលុបតាមឈ្មោះ

    # ==========================================================
    # [លេខ ៩] បង្ហាញព័ត៌មានផ្ទាំងពេញលេញ (ADB Port ឃើញទាំងពេលបិទ/បើក)
    # ==========================================================
    kh.ShowAllInfo(11)

    # ==========================================================
    # [លេខ ១០] ពិនិត្យមើលតែបញ្ជី APK ដែលបានដំឡើង (ភ្ជាប់លេខរៀង 1, 2, 3...)
    # ==========================================================
    kh.ListApps(11)

    # ==========================================================
    # [លេខ ១១] ទាញយក (Download) APK ទាំងអស់មកកុំព្យូទ័រ
    # ==========================================================
    # kh.DownloadAllApks(11, save_dir=r"C:\LDPlayer_APKs")

    # ==========================================================
    # [លេខ ១២] កំណត់ទាញយកតែ APK ណាខ្លះតាមលេខរៀង
    # ==========================================================
    # ឧទាហរណ៍៖ ទាញយកតែ App លេខរៀងទី 1
    # kh.DownloadApkByNumbers(11, numbers=1)

    # ឬទាញយកតាមលេខរៀងច្រើន App ដំណាលគ្នា (លេខ 1 និងលេខ 2)៖
    # kh.DownloadApkByNumbers(11, numbers=[1, 2])

    # ==========================================================
    # [លេខ ១៣] ពិនិត្យមើល IP Public, City, Region, Country និង ISP
    # ==========================================================
    kh.GetPublicIP(11)
