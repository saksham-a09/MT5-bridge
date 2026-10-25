#!/usr/bin/env python3
import os
import sys
import json
import time
import datetime
import argparse
import subprocess
import shutil
import threading
import logging
import psutil

# Check if MetaTrader5 is installed
try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

ORDER_TYPE_NAMES = {
    0: "BUY",
    1: "SELL",
    2: "BUY_LIMIT",
    3: "SELL_LIMIT",
    4: "BUY_STOP",
    5: "SELL_STOP",
    6: "BUY_STOP_LIMIT",
    7: "SELL_STOP_LIMIT"
}

ORDER_TYPE_PENDING_MAP = {
    "BUY_LIMIT": 2,
    "SELL_LIMIT": 3,
    "BUY_STOP": 4,
    "SELL_STOP": 5,
    "BUY_STOP_LIMIT": 6,
    "SELL_STOP_LIMIT": 7
}

def is_wine():
    """Detect if we are running under Wine compatibility layer."""
    import ctypes
    try:
        return hasattr(ctypes.windll.ntdll, 'wine_get_version')
    except Exception:
        pass
    for env_var in ["WINEPREFIX", "WINELOADERNOEXEC", "WINEARCH"]:
        if env_var in os.environ:
            return True
    return False

def validate_terminal_executable(path: str) -> tuple[bool, str]:
    """Validates that a terminal executable path exists and is a valid Windows PE binary (not a Git LFS pointer or empty file)."""
    if not path or not os.path.isfile(path):
        return False, f"Executable not found at path: {path}"
    try:
        size = os.path.getsize(path)
        if size == 0:
            return False, f"Executable file is 0 bytes: {path}"
        with open(path, "rb") as f:
            header = f.read(128)
        if header.startswith(b"version https://git-lfs"):
            return False, (
                f"File '{path}' is a Git LFS pointer text file ({size} bytes), NOT a real binary! "
                "Run 'sudo apt-get install -y git-lfs && git lfs install && git lfs pull' on your Linux host."
            )
        if not header.startswith(b"MZ"):
            return False, f"File '{path}' does not have a valid Windows PE header (expected 'MZ', found {header[:4]!r})."
        if size < 5 * 1024 * 1024:
            return False, f"File '{path}' is suspiciously small ({size} bytes) for an MT5 terminal executable."
        return True, "Valid"
    except Exception as e:
        return False, f"Failed to inspect executable '{path}': {e}"

def update_ini_template(template_content, login, password, server, expert=None, symbol=None, period=None):
    """Case-preserving config.ini generator. Omits empty/invalid Expert to prevent 'Cannot load config on start'."""
    lines = template_content.splitlines()
    new_lines = []
    in_common = False
    in_startup = False
    
    updated_common_fields = {"login": False, "password": False, "server": False}
    updated_startup_fields = {"expert": False, "symbol": False, "period": False}

    valid_expert = str(expert).strip() if expert and str(expert).strip() else None
    valid_symbol = str(symbol).strip() if symbol and str(symbol).strip() else "XAUUSD"
    valid_period = str(period).strip() if period and str(period).strip() else "M1"
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith("[") and stripped.endswith("]"):
            section_name = stripped[1:-1].strip().lower()
            
            if in_common:
                for key in ["login", "password", "server"]:
                    if not updated_common_fields[key]:
                        val = login if key == "login" else (password if key == "password" else server)
                        new_lines.append(f"{key.capitalize()}={val}")
                        updated_common_fields[key] = True
                in_common = False
                
            if in_startup:
                if valid_expert and not updated_startup_fields["expert"]:
                    new_lines.append(f"Expert={valid_expert}")
                    updated_startup_fields["expert"] = True
                if valid_symbol and not updated_startup_fields["symbol"]:
                    new_lines.append(f"Symbol={valid_symbol}")
                    updated_startup_fields["symbol"] = True
                if valid_period and not updated_startup_fields["period"]:
                    new_lines.append(f"Period={valid_period}")
                    updated_startup_fields["period"] = True
                in_startup = False
                
            if section_name == "common":
                in_common = True
            elif section_name == "startup":
                in_startup = True
        
        if in_common and "=" in line and not stripped.startswith(";"):
            key, val = line.split("=", 1)
            key_stripped = key.strip().lower()
            if key_stripped == "login":
                new_lines.append(f"Login={login}")
                updated_common_fields["login"] = True
                continue
            elif key_stripped == "password":
                new_lines.append(f"Password={password}")
                updated_common_fields["password"] = True
                continue
            elif key_stripped == "server":
                new_lines.append(f"Server={server}")
                updated_common_fields["server"] = True
                continue
                
        if in_startup and "=" in line and not stripped.startswith(";"):
            key, val = line.split("=", 1)
            key_stripped = key.strip().lower()
            if key_stripped == "expert":
                if valid_expert:
                    new_lines.append(f"Expert={valid_expert}")
                    updated_startup_fields["expert"] = True
                # If no valid expert, omit this line completely
                continue
            elif key_stripped == "symbol" and valid_symbol:
                new_lines.append(f"Symbol={valid_symbol}")
                updated_startup_fields["symbol"] = True
                continue
            elif key_stripped == "period" and valid_period:
                new_lines.append(f"Period={valid_period}")
                updated_startup_fields["period"] = True
                continue
        
        new_lines.append(line)
        
    if in_common:
        for key in ["login", "password", "server"]:
            if not updated_common_fields[key]:
                val = login if key == "login" else (password if key == "password" else server)
                new_lines.append(f"{key.capitalize()}={val}")
                updated_common_fields[key] = True
                
    if in_startup:
        if valid_expert and not updated_startup_fields["expert"]:
            new_lines.append(f"Expert={valid_expert}")
            updated_startup_fields["expert"] = True
        if valid_symbol and not updated_startup_fields["symbol"]:
            new_lines.append(f"Symbol={valid_symbol}")
            updated_startup_fields["symbol"] = True
        if valid_period and not updated_startup_fields["period"]:
            new_lines.append(f"Period={valid_period}")
            updated_startup_fields["period"] = True
                
    return "\n".join(new_lines)


def trim_working_set(pid=None):
    """Trims unused working set memory pages on Windows/Wine to minimize physical RAM footprint."""
    try:
        import ctypes
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "kernel32"):
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_SET_QUOTA = 0x0100
            target_pid = pid or os.getpid()
            h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, target_pid)
            if h_proc:
                if hasattr(ctypes.windll, "psapi"):
                    ctypes.windll.psapi.EmptyWorkingSet(h_proc)
                ctypes.windll.kernel32.CloseHandle(h_proc)
    except Exception:
        pass


def clean_terminal_logs(clone_dir, logger=None):
    """Purges old MT5 logs and crashdumps to prevent disk growth."""
    for log_dir in [
        os.path.join(clone_dir, "MQL5", "Logs"),
        os.path.join(clone_dir, "Logs"),
        os.path.join(clone_dir, "tester", "logs"),
        os.path.join(clone_dir, "CrashDumps")
    ]:
        if not os.path.isdir(log_dir):
            continue
        try:
            now = time.time()
            for fname in os.listdir(log_dir):
                fpath = os.path.join(log_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                # Remove if older than 2 days (172800s) or > 10MB
                if now - os.path.getmtime(fpath) > 172800 or os.path.getsize(fpath) > 10 * 1024 * 1024:
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
        except Exception:
            pass


def patch_mt5_experts_config(clone_dir, logger=None):
    """Ensures MT5 terminal Config/common.ini and terminal.ini are configured with AutoTrading / Experts enabled
    and optimized for minimal RAM, CPU, and disk usage (disables news, sound, DDE, and caps chart bars)."""
    cfg_dir = os.path.join(clone_dir, "Config")
    os.makedirs(cfg_dir, exist_ok=True)
    
    desired_settings = {
        "experts": {
            "Enabled": "1",
            "AllowLiveTrading": "1",
            "AllowDllImport": "1",
            "ConfirmDllCalls": "0",
            "Notifications": "0",
            "Sound": "0"
        },
        "common": {
            "NewsEnable": "0",
            "EnableNews": "0",
            "SoundEnable": "0",
            "DDEEnable": "0",
            "FtpEnable": "0",
            "MailEnable": "0",
            "CertificatesEnable": "0",
            "CommunityEnable": "0",
            "PushEnable": "0",
            "ProxyEnable": "0"
        },
        "charts": {
            "MaxBars": "10",
            "PrintColor": "0",
            "SaveDeleted": "0",
            "ShowTradeLevels": "0",
            "ShowOHLC": "0",
            "ShowVolumes": "0",
            "ColorMode": "0",
            "AutoScroll": "0",
            "ChartShift": "0"
        }
    }

    for filename in ["common.ini", "terminal.ini"]:
        filepath = os.path.join(cfg_dir, filename)
        encoding = "utf-16le"
        content = ""
        if os.path.isfile(filepath):
            for enc in ["utf-16le", "utf-8", "cp1252"]:
                try:
                    with open(filepath, "r", encoding=enc) as f:
                        test_str = f.read()
                    if test_str and ("[" in test_str or len(test_str) > 0):
                        content = test_str
                        encoding = enc
                        break
                except Exception:
                    continue

        lines = content.splitlines() if content else []
        new_lines = []
        cur_sec = None
        seen_keys = {s: set() for s in desired_settings}
        present_sections = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if cur_sec in desired_settings:
                    for k, v in desired_settings[cur_sec].items():
                        if k.lower() not in seen_keys[cur_sec]:
                            new_lines.append(f"{k}={v}")
                            seen_keys[cur_sec].add(k.lower())
                sec_name = stripped[1:-1].strip().lower()
                cur_sec = sec_name
                if sec_name in desired_settings:
                    present_sections.add(sec_name)
                new_lines.append(line)
                continue

            if cur_sec in desired_settings and "=" in stripped and not stripped.startswith(";"):
                k, _ = stripped.split("=", 1)
                k_clean = k.strip()
                k_lower = k_clean.lower()
                target_key = None
                for dk in desired_settings[cur_sec]:
                    if dk.lower() == k_lower:
                        target_key = dk
                        break

                if target_key:
                    target_val = desired_settings[cur_sec][target_key]
                    new_lines.append(f"{target_key}={target_val}")
                    seen_keys[cur_sec].add(k_lower)
                    continue

            new_lines.append(line)

        if cur_sec in desired_settings:
            for k, v in desired_settings[cur_sec].items():
                if k.lower() not in seen_keys[cur_sec]:
                    new_lines.append(f"{k}={v}")
                    seen_keys[cur_sec].add(k.lower())

        for sec_name, sec_dict in desired_settings.items():
            if sec_name not in present_sections:
                new_lines.append("")
                new_lines.append(f"[{sec_name.capitalize()}]")
                for k, v in sec_dict.items():
                    new_lines.append(f"{k}={v}")

        try:
            out_text = "\n".join(new_lines) + "\n"
            with open(filepath, "w", encoding=encoding) as f:
                f.write(out_text)
            if logger:
                logger.info(f"Configured {filename} (Experts Enabled, low-RAM tuned) ({encoding})")
        except Exception as e:
            if logger:
                logger.warning(f"Could not write {filename}: {e}")


class MT5Worker:
    def __init__(self, login_id, password, server, terminal_path, clone_dir,
                 config_template_path, sync_interval=5, expert=None, symbol=None, timeframe=None, is_master=False):
        self.login_id = int(login_id)
        self.password = str(password)
        self.server = str(server)
        self.terminal_path = os.path.abspath(os.path.normpath(terminal_path))
        self.clone_dir = os.path.abspath(os.path.normpath(clone_dir))
        self.config_template_path = os.path.abspath(os.path.normpath(config_template_path)) if config_template_path else None
        self.sync_interval = sync_interval
        self.is_master = bool(is_master)
        
        self.expert = str(expert).strip() if expert and str(expert).strip() else ""
        self.symbol = str(symbol).strip() if symbol and str(symbol).strip() else "XAUUSD"
        self.timeframe = str(timeframe).strip() if timeframe and str(timeframe).strip() else "M1"
        
        self.telemetry_file = os.path.join(self.clone_dir, "telemetry.json")
        self.mt5_process = None
        self.stop_event = threading.Event()
        self.monitor_thread = None
        
        os.makedirs(self.clone_dir, exist_ok=True)
        self.cmd_dir = os.path.join(self.clone_dir, "commands")
        self.results_dir = os.path.join(self.clone_dir, "results")
        os.makedirs(self.cmd_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        self.executed_commands = set()  # Cache of executed cmd_ids to prevent re-execution
        self.last_pos_sig = None
        self.last_telemetry_data = {}
        self.last_mem_trim = 0
        self.last_deals_time = 0
        self.cached_deals = None
        self.cached_daily_closed_pnl = 0.0
        self.urgent_telemetry_file = os.path.join(self.clone_dir, "urgent_telemetry.json")

        self.terminal_pid = None
        pid_file = os.path.join(self.clone_dir, "terminal.pid")
        if os.path.isfile(pid_file):
            try:
                with open(pid_file, "r") as pf:
                    cand_pid = int(pf.read().strip())
                    if psutil.pid_exists(cand_pid):
                        self.terminal_pid = cand_pid
            except Exception:
                pass

        log_file = os.path.join(self.clone_dir, f"worker_{self.login_id}.log")
        
        self.logger = logging.getLogger(f"Worker_{self.login_id}")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(fh)
            if sys.stdout is not None:
                sh = logging.StreamHandler(sys.stdout)
                sh.setFormatter(logging.Formatter(f'[Worker {self.login_id}] %(asctime)s - %(levelname)s - %(message)s'))
                self.logger.addHandler(sh)
        
        self.logger.info("Worker instance initialized.")
        patch_mt5_experts_config(self.clone_dir, self.logger)

    def minimize_terminal_window(self):
        """Minimizes the MT5 terminal window (SW_MINIMIZE) to disable GDI painting & WM_PAINT messages,
        reducing terminal CPU footprint by up to 70% while keeping MQL5 and Python API at 100% speed."""
        try:
            import ctypes
            if not hasattr(ctypes, "windll") or not hasattr(ctypes.windll, "user32"):
                return False
            user32 = ctypes.windll.user32
            target_pids = set()
            if self.terminal_pid:
                target_pids.add(self.terminal_pid)
            if self.mt5_process and self.mt5_process.pid:
                target_pids.add(self.mt5_process.pid)

            proc = self.get_terminal_process()
            if proc and proc.pid:
                target_pids.add(proc.pid)

            if not target_pids:
                return False

            SW_MINIMIZE = 6
            hwnds = []

            def enum_proc(hwnd, lparam):
                if user32.IsWindow(hwnd):
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in target_pids:
                        hwnds.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

            # Fallback by window title if no HWND found directly by PID
            if not hwnds:
                login_str = str(self.login_id)
                def enum_fallback(hwnd, lparam):
                    if user32.IsWindow(hwnd):
                        buf = ctypes.create_unicode_buffer(512)
                        user32.GetWindowTextW(hwnd, buf, 512)
                        cbuf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(hwnd, cbuf, 256)
                        if login_str in buf.value or "MetaTrader" in buf.value or "MetaQuotes" in cbuf.value:
                            hwnds.append(hwnd)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_fallback), 0)

            minimized_count = 0
            for h in hwnds:
                user32.ShowWindow(h, SW_MINIMIZE)
                minimized_count += 1

            if minimized_count > 0:
                self.logger.info(f"CPU Tuning: Minimized {minimized_count} MT5 window(s) to suppress GDI redraws (SW_MINIMIZE).")
                return True
        except Exception as e:
            self.logger.debug(f"Window minimize skipped or unavailable: {e}")
        return False

    def optimize_process_priority(self):
        """Sets BELOW_NORMAL priority for terminal and worker process to prevent CPU starvation under high multi-terminal density."""
        try:
            cur_p = psutil.Process(os.getpid())
            if os.name == "nt":
                cur_p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                cur_p.nice(10)
        except Exception:
            pass

        try:
            term_proc = self.get_terminal_process()
            if term_proc:
                if os.name == "nt":
                    term_proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                else:
                    term_proc.nice(10)
        except Exception:
            pass

    def prune_market_watch(self):
        """Hides untraded symbols from Market Watch so MT5 stops receiving and processing unnecessary tick streams on CPU."""
        if not mt5:
            return
        try:
            active_symbols = set()
            if self.symbol:
                active_symbols.add(self.symbol.strip().upper())

            positions = mt5.positions_get()
            if positions:
                for p in positions:
                    if p.symbol:
                        active_symbols.add(p.symbol.strip().upper())

            orders = mt5.orders_get()
            if orders:
                for o in orders:
                    if o.symbol:
                        active_symbols.add(o.symbol.strip().upper())

            if not active_symbols:
                active_symbols.add("XAUUSD")

            # Keep active symbols enabled
            for sym in active_symbols:
                mt5.symbol_select(sym, True)

            # Prune all other selected symbols
            all_selected = mt5.symbols_get(selected=True) or ()
            hidden = 0
            for s in all_selected:
                if s.name.upper() not in active_symbols:
                    if mt5.symbol_select(s.name, False):
                        hidden += 1
            if hidden > 0:
                self.logger.info(f"CPU Tuning: Pruned {hidden} inactive symbols from Market Watch (Active: {list(active_symbols)}).")
        except Exception as e:
            self.logger.debug(f"Market Watch pruning skipped: {e}")

    def ensure_autotrading_enabled(self):
        """Checks if MT5 terminal has AlgoTrading (automated trading) enabled. If not, auto-enables via Win32."""
        if not mt5:
            return False
        try:
            t_info = mt5.terminal_info()
            if t_info and getattr(t_info, "trade_allowed", False):
                return True

            self.logger.warning("MT5 AutoTrading is DISABLED (trade_allowed=False). Auto-enabling via Windows GUI message...")
            import ctypes
            user32 = ctypes.windll.user32

            target_pids = set()
            if self.mt5_process and self.mt5_process.pid:
                target_pids.add(self.mt5_process.pid)
            proc = self.get_terminal_process()
            if proc and proc.pid:
                target_pids.add(proc.pid)

            hwnds = []
            def enum_proc(hwnd, lparam):
                if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                    pid = ctypes.c_ulong()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value in target_pids:
                        hwnds.append(hwnd)
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)

            # Fallback: if no hwnds found by PID, check by window title/class
            if not hwnds:
                login_str = str(self.login_id)
                def enum_fallback(hwnd, lparam):
                    if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                        buf = ctypes.create_unicode_buffer(512)
                        user32.GetWindowTextW(hwnd, buf, 512)
                        cbuf = ctypes.create_unicode_buffer(256)
                        user32.GetClassNameW(hwnd, cbuf, 256)
                        if login_str in buf.value or "MetaTrader" in buf.value or "MetaQuotes" in cbuf.value:
                            hwnds.append(hwnd)
                    return True
                user32.EnumWindows(WNDENUMPROC(enum_fallback), 0)

            WM_COMMAND = 0x0111
            MT5_CMD_AUTOTRADING = 32851  # ID_EXPERTS_ENABLE

            for h in hwnds:
                user32.PostMessageW(h, WM_COMMAND, MT5_CMD_AUTOTRADING, 0)

            time.sleep(0.5)
            t_info2 = mt5.terminal_info()
            if t_info2 and getattr(t_info2, "trade_allowed", False):
                self.logger.info("Successfully enabled AutoTrading on MT5 terminal!")
                return True
            else:
                self.logger.warning(
                    "AutoTrading toggle sent. If still disabled, please click 'Algo Trading' (Ctrl+E) in MT5 terminal."
                )
                return False
        except Exception as e:
            self.logger.warning(f"Could not auto-toggle AutoTrading: {e}")
            return False

    def _has_executable(self):
        for name in ["terminal64.exe", "terminal.exe"]:
            p = os.path.join(self.clone_dir, name)
            if os.path.isfile(p):
                valid, reason = validate_terminal_executable(p)
                if valid:
                    return True
                else:
                    self.logger.warning(f"Corrupted or invalid executable in clone dir '{p}': {reason}. Removing to force re-clone.")
                    try:
                        os.remove(p)
                    except Exception:
                        pass
        return False

    def _get_executable(self):
        for name in ["terminal64.exe", "terminal.exe"]:
            p = os.path.join(self.clone_dir, name)
            if os.path.isfile(p):
                valid, _ = validate_terminal_executable(p)
                if valid:
                    return p
                else:
                    try:
                        os.remove(p)
                    except Exception:
                        pass

        if os.path.isfile(self.terminal_path):
            valid, reason = validate_terminal_executable(self.terminal_path)
            if not valid:
                self.logger.critical(f"Master terminal executable invalid: {reason}")
                return None
            shutil_dest = os.path.join(self.clone_dir, os.path.basename(self.terminal_path))
            try:
                try:
                    os.link(self.terminal_path, shutil_dest)
                    self.logger.info(f"Hard-linked terminal executable to {shutil_dest} (shared memory pages)")
                except OSError:
                    shutil.copy2(self.terminal_path, shutil_dest)
                    self.logger.info(f"Copied terminal executable to {shutil_dest}")
                return shutil_dest
            except Exception as e:
                self.logger.error(f"Failed to link/copy terminal executable: {e}")
                return None
        return None

    def launch_mt5(self):
        """Starts the MT5 terminal process in portable mode with cleared charts and hard-linked static binaries."""
        # 0. Clean stale logs and crash dumps
        clean_terminal_logs(self.clone_dir, self.logger)

        # 1. Clone directory if executable missing
        if not self._has_executable():
            master_dir = os.path.dirname(self.terminal_path) if os.path.isfile(self.terminal_path) else self.terminal_path
            self.logger.info(f"Clone directory does not contain terminal. Cloning from master: {master_dir}")
            if not os.path.isdir(master_dir):
                self.logger.error(f"Master MT5 directory '{master_dir}' does not exist.")
                return False

            # Pre-check master executable validity before cloning
            for exe_name in ["terminal64.exe", "terminal.exe"]:
                m_exe = os.path.join(master_dir, exe_name)
                if os.path.isfile(m_exe):
                    m_valid, m_reason = validate_terminal_executable(m_exe)
                    if not m_valid:
                        self.logger.critical(f"Master MT5 binary is invalid: {m_reason}")
                        return False
                    break

            try:
                # Intelligent link-cloner: hard-link static read-only files (saving disk & sharing page cache in RAM)
                hard_linked = 0
                copied = 0
                for root, dirs, files in os.walk(master_dir):
                    rel_path = os.path.relpath(root, master_dir)
                    if rel_path != ".":
                        top_dir = rel_path.split(os.sep)[0].lower()
                        if top_dir in ("bases", "sounds", "help", "tester", "templates", "crashdumps"):
                            continue
                    dest_dir = os.path.join(self.clone_dir, rel_path) if rel_path != "." else self.clone_dir
                    os.makedirs(dest_dir, exist_ok=True)
                    for file in files:
                        f_lower = file.lower()
                        if f_lower.endswith((".log", ".dmp", ".tmp", ".wav", ".mp3", ".pdf", ".chm")):
                            continue
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_dir, file)
                        if os.path.exists(dst_file):
                            continue
                        # If file is config or custom profile, copy it independently so instances don't collide
                        is_instance_specific = (
                            f_lower in ("config.ini", "common.ini", "terminal.ini") or
                            "profiles" in rel_path.lower() or
                            "logs" in rel_path.lower()
                        )
                        if is_instance_specific:
                            try:
                                shutil.copy2(src_file, dst_file)
                                copied += 1
                            except Exception:
                                pass
                        else:
                            try:
                                os.link(src_file, dst_file)
                                hard_linked += 1
                            except OSError:
                                shutil.copy2(src_file, dst_file)
                                copied += 1

                self.logger.info(f"Cloned MT5 structure: {hard_linked} hard-links (RAM/disk optimized), {copied} copied files.")
            except Exception as e:
                self.logger.error(f"Failed to clone master MT5 directory: {e}")
                return False

        executable = self._get_executable()
        if not executable:
            self.logger.error("No valid MT5 terminal executable found.")
            return False

        valid, reason = validate_terminal_executable(executable)
        if not valid:
            self.logger.critical(f"Aborting launch: {reason}")
            return False

        # 2. Generate config.ini
        if self.config_template_path and os.path.exists(self.config_template_path):
            try:
                with open(self.config_template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()
                
                updated_content = update_ini_template(
                    template_content,
                    str(self.login_id),
                    self.password,
                    self.server,
                    expert=self.expert if self.expert else None,
                    symbol=self.symbol if self.symbol else None,
                    period=self.timeframe if self.timeframe else None
                )
                dest_ini_path = os.path.join(self.clone_dir, "config.ini")
                with open(dest_ini_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                self.logger.info(f"Wrote config.ini for {self.login_id} ({self.server})")
            except Exception as e:
                self.logger.error(f"Failed to generate config.ini: {e}")
                return False

        # 3. Clear chart profiles (crucial to keep memory usage minimal)
        for charts_root in [
            os.path.join(self.clone_dir, "MQL5", "Profiles", "Charts"),
            os.path.join(self.clone_dir, "Profiles", "Charts")
        ]:
            if not os.path.isdir(charts_root):
                continue
            for profile_name in os.listdir(charts_root):
                profile_dir = os.path.join(charts_root, profile_name)
                if not os.path.isdir(profile_dir):
                    continue
                try:
                    for item in os.listdir(profile_dir):
                        if item.endswith(".chr"):
                            os.remove(os.path.join(profile_dir, item))
                except Exception as e:
                    self.logger.warning(f"Could not clear charts in {profile_dir}: {e}")

        # 4. Clear stale temp lock files and unnecessary cache folders
        for bloat_dir in ["temp", "CrashDumps", "Tester", "Sounds", "Help"]:
            p = os.path.join(self.clone_dir, bloat_dir)
            if os.path.isdir(p):
                try:
                    shutil.rmtree(p, ignore_errors=True)
                except Exception:
                    pass

        # Ensure AutoTrading is configured in terminal ini files with low-RAM parameters
        patch_mt5_experts_config(self.clone_dir, self.logger)

        # 5. Launch terminal in portable mode
        creation_flags = 0
        if os.name == "nt" and not is_wine():
            creation_flags = subprocess.CREATE_NEW_CONSOLE

        abs_executable = os.path.abspath(executable)
        abs_clone_dir = os.path.abspath(self.clone_dir)

        # In portable mode with cwd=abs_clone_dir, /config:config.ini reliably loads config.ini from cwd without space/path quoting issues
        cmd_str = f'"{abs_executable}" /portable /config:config.ini'
        self.logger.info(f"Launching MT5: {cmd_str} in cwd: {abs_clone_dir}")

        try:
            self.mt5_process = subprocess.Popen(
                cmd_str,
                cwd=abs_clone_dir,
                creationflags=creation_flags
            )
            self.terminal_pid = self.mt5_process.pid
            try:
                with open(os.path.join(self.clone_dir, "terminal.pid"), "w") as pf:
                    pf.write(str(self.terminal_pid))
            except Exception:
                pass
            self.logger.info(f"MT5 spawned (PID: {self.mt5_process.pid})")
            startup_wait = 18 if is_wine() else 10
            time.sleep(startup_wait)
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch MT5 process: {e}")
            return False

    def connect_mt5(self):
        """Initializes connection to the MT5 terminal via MetaTrader5 python API."""
        if mt5 is None:
            self.logger.error("MetaTrader5 python module is not available in this environment.")
            return False

        executable = self._get_executable()
        if not executable:
            return False

        max_attempts = 3
        timeout_ms = 25000

        for attempt in range(1, max_attempts + 1):
            if not self.is_terminal_running():
                self.logger.warning("Terminal process is not running. Aborting API binding attempt.")
                return False

            success = False
            try:
                # Direct bind to running instance
                success = mt5.initialize(
                    path=executable,
                    timeout=timeout_ms,
                    portable=True
                )
                if not success:
                    # Fallback with explicit credentials
                    success = mt5.initialize(
                        path=executable,
                        login=self.login_id,
                        password=self.password,
                        server=self.server,
                        timeout=timeout_ms,
                        portable=True
                    )
            except Exception as e:
                self.logger.error(f"Exception during mt5.initialize(): {e}")
                success = False

            if success:
                self.logger.info("Bound to MetaTrader5 API successfully.")
                acc = mt5.account_info()
                if acc is None or acc.login != self.login_id:
                    self.logger.info(f"Logging explicitly into {self.login_id}...")
                    if not mt5.login(self.login_id, password=self.password, server=self.server, timeout=timeout_ms):
                        self.logger.warning(f"mt5.login() error: {mt5.last_error()}")
                    else:
                        self.logger.info(f"Logged into MT5 account {self.login_id}.")
                self.ensure_autotrading_enabled()
                self.prune_market_watch()
                self.optimize_process_priority()
                # Close all open charts to eliminate raster and bar array allocations in RAM
                try:
                    open_charts = mt5.charts_get() or ()
                    for c in open_charts:
                        mt5.chart_close(c)
                    if open_charts:
                        self.logger.info(f"Closed {len(open_charts)} active chart(s) for 0-chart low-RAM operation.")
                except Exception:
                    pass
                # Minimize window to suppress GDI redraws (huge CPU saver)
                self.minimize_terminal_window()
                return True
            else:
                self.logger.warning(f"MT5 init attempt {attempt}/{max_attempts} failed: {mt5.last_error()}")
                if attempt < max_attempts:
                    time.sleep(3)

        return False

    def get_terminal_process(self):
        """Finds active terminal process running from this clone directory (cached by PID)."""
        if self.terminal_pid:
            try:
                if psutil.pid_exists(self.terminal_pid):
                    p = psutil.Process(self.terminal_pid)
                    if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                        return p
            except Exception:
                pass
            self.terminal_pid = None

        try:
            my_pid = os.getpid()
            clone_dir_abs = os.path.abspath(self.clone_dir).lower()
            clone_name = os.path.basename(self.clone_dir).lower()
            try:
                procs = list(psutil.process_iter())
            except Exception:
                procs = []
            for proc in procs:
                try:
                    if proc.pid == my_pid:
                        continue
                    exe = None
                    try:
                        exe = proc.exe()
                    except Exception:
                        pass
                    if exe and os.path.abspath(exe).lower().startswith(clone_dir_abs):
                        self.terminal_pid = proc.pid
                        return proc
                    cmdline = []
                    try:
                        cmdline = proc.cmdline() or []
                    except Exception:
                        pass
                    cmdline_str = " ".join(cmdline).lower()
                    if "worker.py" in cmdline_str:
                        continue
                    name = ''
                    try:
                        name = (proc.name() or '').lower()
                    except Exception:
                        pass
                    if ("terminal" in name or "wine" in name) and (clone_dir_abs in cmdline_str or clone_name in cmdline_str):
                        self.terminal_pid = proc.pid
                        return proc
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def is_terminal_running(self):
        if self.mt5_process is not None and self.mt5_process.poll() is None:
            return True
        if self.terminal_pid:
            try:
                if psutil.pid_exists(self.terminal_pid):
                    p = psutil.Process(self.terminal_pid)
                    if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                        return True
            except Exception:
                pass
            self.terminal_pid = None
        proc = self.get_terminal_process()
        if proc is not None and proc.is_running():
            return True
        try:
            if mt5 and mt5.terminal_info() is not None:
                return True
        except Exception:
            pass
        return False

    def check_connection(self):
        try:
            if not mt5:
                return False
            t_info = mt5.terminal_info()
            a_info = mt5.account_info()
            return bool(t_info and a_info and t_info.connected)
        except Exception:
            return False

    def collect_telemetry(self):
        """Extracts complete telemetry and writes to local atomic JSON."""
        data = {
            "login": self.login_id,
            "is_connected": False,
            "broker_name": "",
            "server": self.server,
            "currency": "USD",
            "leverage": 100,
            "balance": 0.0,
            "equity": 0.0,
            "profit": 0.0,
            "margin": 0.0,
            "margin_free": 0.0,
            "margin_level": 0.0,
            "ping": 0,
            "open_positions": [],
            "pending_orders": [],
            "deals_history": [],
            "daily_closed_pnl": 0.0,
            "error_message": "",
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            if mt5:
                t_info = mt5.terminal_info()
                a_info = mt5.account_info()

                if t_info and a_info:
                    trade_allowed = bool(getattr(t_info, "trade_allowed", False))
                    data["is_connected"] = bool(t_info.connected)
                    data["trade_allowed"] = trade_allowed
                    data["account_trade_allowed"] = bool(getattr(a_info, "trade_allowed", False))
                    data["ping"] = getattr(t_info, "ping_last", 0)
                    data["broker_name"] = getattr(a_info, "company", "")
                    data["currency"] = getattr(a_info, "currency", "USD")
                    data["leverage"] = getattr(a_info, "leverage", 100)
                    data["balance"] = round(getattr(a_info, "balance", 0.0), 2)
                    data["equity"] = round(getattr(a_info, "equity", 0.0), 2)
                    data["profit"] = round(getattr(a_info, "profit", 0.0), 2)
                    data["margin"] = round(getattr(a_info, "margin", 0.0), 2)
                    data["margin_free"] = round(getattr(a_info, "margin_free", 0.0), 2)
                    data["margin_level"] = round(getattr(a_info, "margin_level", 0.0), 2)

                    if not trade_allowed:
                        data["error_message"] = "AutoTrading disabled in MT5 (click Algo Trading or Ctrl+E)"

                    # Open positions
                    positions = mt5.positions_get()
                    if positions:
                        pos_list = []
                        for p in positions:
                            pos_list.append({
                                "ticket": p.ticket,
                                "symbol": p.symbol,
                                "type": "BUY" if p.type == 0 else "SELL",
                                "volume": p.volume,
                                "price_open": p.price_open,
                                "price_current": p.price_current,
                                "sl": p.sl,
                                "tp": p.tp,
                                "profit": round(p.profit, 2),
                                "swap": round(p.swap, 2),
                                "comment": p.comment,
                                "time": datetime.datetime.fromtimestamp(p.time, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                            })
                        data["open_positions"] = pos_list

                    # Pending orders
                    orders = mt5.orders_get()
                    orders_list = []
                    if orders:
                        for o in orders:
                            type_name = ORDER_TYPE_NAMES.get(o.type, "PENDING")
                            orders_list.append({
                                "ticket": o.ticket,
                                "symbol": o.symbol,
                                "type": type_name,
                                "volume": o.volume_current if getattr(o, "volume_current", 0) > 0 else o.volume_initial,
                                "price_open": o.price_open,
                                "price_current": getattr(o, "price_current", 0.0),
                                "sl": o.sl,
                                "tp": o.tp,
                                "stoplimit": getattr(o, "price_stoplimit", 0.0),
                                "comment": o.comment,
                                "time": datetime.datetime.fromtimestamp(o.time_setup, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if getattr(o, "time_setup", 0) else ""
                            })
                    data["pending_orders"] = orders_list

                    # Recent history deals (last 5) & today's closed PnL - cached every 15s to conserve CPU
                    now_ts = time.time()
                    if now_ts - self.last_deals_time >= 15.0 or self.cached_deals is None:
                        self.last_deals_time = now_ts
                        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
                        date_to = now + datetime.timedelta(days=1)
                        date_from = now - datetime.timedelta(days=7)
                        deals = mt5.history_deals_get(date_from, date_to)
                        recent_deals = []
                        today_utc_date = datetime.datetime.now(datetime.timezone.utc).date()
                        today_local_date = datetime.datetime.now().date()
                        today_closed_sum = 0.0
                        if deals:
                            for d in deals:
                                if d.entry in (1, 2, 3) and getattr(d, "symbol", ""):
                                    deal_utc = datetime.datetime.fromtimestamp(d.time, datetime.timezone.utc).date()
                                    deal_loc = datetime.datetime.fromtimestamp(d.time).date()
                                    if deal_utc in (today_utc_date, today_local_date) or deal_loc in (today_utc_date, today_local_date):
                                        p = float(getattr(d, "profit", 0.0) or 0.0)
                                        sw = float(getattr(d, "swap", 0.0) or 0.0)
                                        comm = float(getattr(d, "commission", 0.0) or 0.0)
                                        fee = float(getattr(d, "fee", 0.0) or 0.0)
                                        today_closed_sum += (p + sw + comm + fee)

                            for d in reversed(deals[-10:]):
                                if d.entry in (1, 2, 3) and d.symbol:
                                    p = float(getattr(d, "profit", 0.0) or 0.0)
                                    sw = float(getattr(d, "swap", 0.0) or 0.0)
                                    comm = float(getattr(d, "commission", 0.0) or 0.0)
                                    fee = float(getattr(d, "fee", 0.0) or 0.0)
                                    recent_deals.append({
                                        "ticket": d.ticket,
                                        "symbol": d.symbol,
                                        "type": "BUY" if d.type == 0 else "SELL",
                                        "volume": d.volume,
                                        "price": d.price,
                                        "profit": round(p + sw + comm + fee, 2),
                                        "time": datetime.datetime.fromtimestamp(d.time, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                                    })
                        self.cached_daily_closed_pnl = round(today_closed_sum, 2)
                        self.cached_deals = recent_deals[:5]
                    data["deals_history"] = self.cached_deals or []
                    data["daily_closed_pnl"] = getattr(self, "cached_daily_closed_pnl", 0.0)
                else:
                    data["error_message"] = "Terminal or Account info is null."
        except Exception as e:
            data["error_message"] = str(e)

        # Write atomically with retry for Windows file locks
        self.last_telemetry_data = data.copy()
        temp_path = f"{self.telemetry_file}.tmp"
        written = False
        for attempt in range(4):
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f)
                os.replace(temp_path, self.telemetry_file)
                written = True
                break
            except (PermissionError, OSError):
                time.sleep(0.04)

        if not written:
            try:
                with open(self.telemetry_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception as e:
                self.logger.error(f"Failed to write telemetry file: {e}")

        # Periodic working set memory trim (every 60s)
        now_ts = time.time()
        if now_ts - self.last_mem_trim >= 60.0:
            self.last_mem_trim = now_ts
            trim_working_set(os.getpid())
            proc = self.get_terminal_process()
            if proc and proc.pid:
                trim_working_set(proc.pid)
            try:
                import gc
                gc.collect()
            except Exception:
                pass

    def check_fast_position_changes(self):
        """High-frequency (15ms) scanner to detect trade open/close/modify and pending orders instantly."""
        if not mt5 or not self.is_terminal_running():
            return

        try:
            positions = mt5.positions_get()
            orders = mt5.orders_get()
        except Exception:
            return

        if positions is None and orders is None:
            return

        pos_sig = tuple(sorted(
            (p.ticket, p.symbol, p.type, round(p.volume, 2), round(p.price_open, 5), round(p.sl, 5), round(p.tp, 5))
            for p in (positions or ())
        ))
        order_sig = tuple(sorted(
            (o.ticket, o.symbol, o.type, round(getattr(o, 'volume_current', o.volume_initial), 2), round(o.price_open, 5), round(o.sl, 5), round(o.tp, 5), round(getattr(o, "price_stoplimit", 0.0), 5))
            for o in (orders or ())
        ))
        curr_sig = (pos_sig, order_sig)

        if self.last_pos_sig is None:
            self.last_pos_sig = curr_sig
            return

        if curr_sig != self.last_pos_sig:
            old_pos_count = len(self.last_pos_sig[0]) if self.last_pos_sig else 0
            if len(pos_sig) < old_pos_count:
                self.last_deals_time = 0
            self.last_pos_sig = curr_sig
            self.write_urgent_positions(positions or (), orders or ())

    def write_urgent_positions(self, positions, orders=None):
        """Emits an immediate high-priority telemetry payload when trade state or pending orders change."""
        pos_list = []
        for p in positions:
            pos_list.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": round(p.profit, 2),
                "swap": round(p.swap, 2),
                "comment": p.comment,
                "time": datetime.datetime.fromtimestamp(p.time, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            })

        orders_list = []
        if orders is None and mt5:
            try:
                orders = mt5.orders_get() or ()
            except Exception:
                orders = ()
        for o in (orders or ()):
            type_name = ORDER_TYPE_NAMES.get(o.type, "PENDING")
            orders_list.append({
                "ticket": o.ticket,
                "symbol": o.symbol,
                "type": type_name,
                "volume": o.volume_current if getattr(o, "volume_current", 0) > 0 else o.volume_initial,
                "price_open": o.price_open,
                "price_current": getattr(o, "price_current", 0.0),
                "sl": o.sl,
                "tp": o.tp,
                "stoplimit": getattr(o, "price_stoplimit", 0.0),
                "comment": o.comment,
                "time": datetime.datetime.fromtimestamp(o.time_setup, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if getattr(o, "time_setup", 0) else ""
            })

        payload = self.last_telemetry_data.copy() if self.last_telemetry_data else {
            "login": self.login_id,
            "is_connected": True,
            "broker_name": "",
            "server": self.server,
            "currency": "USD",
            "leverage": 100,
            "balance": 0.0,
            "equity": 0.0,
            "profit": 0.0,
            "margin": 0.0,
            "margin_free": 0.0,
            "margin_level": 0.0,
            "ping": 0,
            "open_positions": [],
            "pending_orders": [],
            "deals_history": [],
            "daily_closed_pnl": getattr(self, "cached_daily_closed_pnl", 0.0),
            "error_message": ""
        }
        payload["login"] = self.login_id
        payload["open_positions"] = pos_list
        payload["pending_orders"] = orders_list
        payload["daily_closed_pnl"] = getattr(self, "cached_daily_closed_pnl", 0.0)
        payload["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        temp_u = f"{self.urgent_telemetry_file}.tmp"
        try:
            with open(temp_u, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(temp_u, self.urgent_telemetry_file)

            temp_t = f"{self.telemetry_file}.tmp"
            with open(temp_t, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(temp_t, self.telemetry_file)
        except Exception:
            pass

    def kill_process(self):
        """Terminates active MT5 processes running from this clone folder."""
        if self.mt5_process:
            try:
                if self.mt5_process.poll() is None:
                    self.mt5_process.terminate()
                    self.mt5_process.wait(timeout=3)
            except Exception:
                try:
                    self.mt5_process.kill()
                except Exception:
                    pass
            finally:
                self.mt5_process = None

        try:
            my_pid = os.getpid()
            clone_dir_abs = os.path.abspath(self.clone_dir).lower()
            clone_name = os.path.basename(self.clone_dir).lower()
            try:
                procs = list(psutil.process_iter())
            except Exception:
                procs = []
            for proc in procs:
                try:
                    if proc.pid == my_pid:
                        continue
                    cmdline = []
                    try:
                        cmdline = proc.cmdline() or []
                    except Exception:
                        pass
                    cmdline_str = " ".join(cmdline).lower()
                    if "worker.py" in cmdline_str:
                        continue
                    exe = None
                    try:
                        exe = proc.exe()
                    except Exception:
                        pass
                    name = ''
                    try:
                        name = (proc.name() or '').lower()
                    except Exception:
                        pass
                    matches_dir = exe and os.path.abspath(exe).lower().startswith(clone_dir_abs)
                    matches_cmd = ("terminal" in name or "wine" in name) and (clone_dir_abs in cmdline_str or clone_name in cmdline_str)
                    if matches_dir or matches_cmd:
                        proc.kill()
                        proc.wait(timeout=2)
                except Exception:
                    pass
        except Exception as e:
            self.logger.error(f"Error terminating processes: {e}")

    def execute_trade_command(self, cmd_id, cmd):
        """Executes a trade order (OPEN, CLOSE, MODIFY_SLTP) with filling mode fallbacks."""
        if not mt5 or not self.check_connection():
            return {"status": "failed", "error": "MT5 terminal not connected"}

        # Ensure automated trading is allowed
        t_info = mt5.terminal_info()
        if t_info and not getattr(t_info, "trade_allowed", False):
            self.ensure_autotrading_enabled()
            t_info = mt5.terminal_info()
            if t_info and not getattr(t_info, "trade_allowed", False):
                err = "AutoTrading disabled by client in MT5. Please click 'Algo Trading' (Ctrl+E) in MT5 terminal."
                self.logger.error(err)
                return {"status": "failed", "error": err}

        start_time = time.time()
        action = str(cmd.get("action", "")).upper()
        symbol = cmd.get("symbol", self.symbol)

        # Ensure symbol is visible in Market Watch
        mt5.symbol_select(symbol, True)
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return {"status": "failed", "error": f"Symbol {symbol} not found on broker"}

        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return {"status": "failed", "error": f"No tick price available for {symbol}"}

        # 1. OPEN NEW POSITION
        if action == "OPEN":
            master_ticket = cmd.get("master_ticket")
            if master_ticket:
                tag = f"C:{master_ticket}"
                open_positions = mt5.positions_get() or ()
                existing = next((p for p in open_positions if tag in p.comment), None)
                if existing:
                    self.logger.warning(
                        f"Position with tag '{tag}' already exists on terminal (Ticket #{existing.ticket}). Skipping duplicate OPEN."
                    )
                    return {
                        "status": "success",
                        "action": "OPEN",
                        "data": {
                            "group_id": cmd.get("group_id"),
                            "master_login": cmd.get("master_login"),
                            "slave_login": self.login_id,
                            "master_ticket": master_ticket,
                            "slave_ticket": existing.ticket,
                            "slave_deal": getattr(existing, 'deal', 0),
                            "symbol": existing.symbol,
                            "order_type": cmd.get("order_type", "BUY"),
                            "master_volume": cmd.get("volume"),
                            "slave_volume": existing.volume,
                            "master_open_price": cmd.get("master_open_price", 0.0),
                            "slave_open_price": existing.price_open,
                            "execution_ms": 0
                        }
                    }

            order_type_str = str(cmd.get("order_type", "BUY")).upper()
            mt5_order_type = mt5.ORDER_TYPE_BUY if order_type_str == "BUY" else mt5.ORDER_TYPE_SELL
            price = tick.ask if order_type_str == "BUY" else tick.bid

            # Volume normalization
            req_vol = float(cmd.get("volume", 0.01))
            step = symbol_info.volume_step or 0.01
            norm_vol = max(symbol_info.volume_min, min(symbol_info.volume_max, round(round(req_vol / step) * step, 2)))

            sl = float(cmd.get("sl", 0.0))
            tp = float(cmd.get("tp", 0.0))
            deviation = int(cmd.get("deviation", 20))
            # Crypto and high-volatility symbols like BTCUSD need wider deviation to avoid requotes
            if "BTC" in symbol.upper() or "ETH" in symbol.upper() or "CRYPTO" in symbol.upper() or (tick.bid > 1000):
                deviation = max(deviation, 300)

            magic = int(cmd.get("magic", 888000))
            comment = str(cmd.get("comment", f"C:{cmd.get('master_ticket', '')}"))

            # Determine best filling mode supported by broker
            filling_modes = []
            f_mode = getattr(symbol_info, "filling_mode", 0)
            if f_mode & 2:
                filling_modes.append(mt5.ORDER_FILLING_IOC)
            if f_mode & 1:
                filling_modes.append(mt5.ORDER_FILLING_FOK)
            filling_modes.append(mt5.ORDER_FILLING_RETURN)
            filling_modes = list(dict.fromkeys(filling_modes))

            last_result = None
            for f in filling_modes:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "volume": norm_vol,
                    "type": mt5_order_type,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": deviation,
                    "magic": magic,
                    "comment": comment,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": f
                }
                res = mt5.order_send(request)
                last_result = res
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    exec_ms = int((time.time() - start_time) * 1000)
                    self.logger.info(f"OPEN SUCCESS Ticket #{res.order} (deal: {res.deal}) in {exec_ms}ms")
                    return {
                        "status": "success",
                        "action": "OPEN",
                        "data": {
                            "group_id": cmd.get("group_id"),
                            "master_login": cmd.get("master_login"),
                            "slave_login": self.login_id,
                            "master_ticket": cmd.get("master_ticket"),
                            "slave_ticket": res.order,
                            "slave_deal": res.deal,
                            "symbol": symbol,
                            "order_type": order_type_str,
                            "master_volume": cmd.get("volume"),
                            "slave_volume": norm_vol,
                            "master_open_price": cmd.get("master_open_price", 0.0),
                            "slave_open_price": res.price or price,
                            "execution_ms": exec_ms
                        }
                    }
                if res and res.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
                    break

            err_msg = f"order_send failed: retcode={getattr(last_result, 'retcode', 'N/A')}, comment={getattr(last_result, 'comment', 'N/A')}"
            self.logger.error(err_msg)
            return {"status": "failed", "action": "OPEN", "error": err_msg}

        # 2. CLOSE EXISTING POSITION
        elif action == "CLOSE":
            slave_ticket = cmd.get("slave_ticket")
            master_ticket = cmd.get("master_ticket")

            target_pos = None
            open_positions = mt5.positions_get() or ()
            if slave_ticket:
                target_pos = next((p for p in open_positions if p.ticket == int(slave_ticket)), None)
            if not target_pos and master_ticket:
                tag = f"C:{master_ticket}"
                target_pos = next((p for p in open_positions if tag in p.comment), None)

            if not target_pos:
                pending_orders = mt5.orders_get() or ()
                target_order = None
                if slave_ticket:
                    target_order = next((o for o in pending_orders if o.ticket == int(slave_ticket)), None)
                if not target_order and master_ticket:
                    tag = f"C:{master_ticket}"
                    target_order = next((o for o in pending_orders if tag in o.comment), None)
                if target_order:
                    cancel_req = {
                        "action": getattr(mt5, "TRADE_ACTION_REMOVE", 8),
                        "order": target_order.ticket
                    }
                    mt5.order_send(cancel_req)
                    return {
                        "status": "success",
                        "action": "CLOSE",
                        "data": {
                            "master_ticket": master_ticket,
                            "slave_ticket": target_order.ticket,
                            "profit": 0.0
                        }
                    }
                self.logger.warning(f"Position for close not found (slave: {slave_ticket}, master: {master_ticket}). Already closed.")
                return {
                    "status": "success",
                    "action": "CLOSE",
                    "data": {
                        "master_ticket": master_ticket,
                        "slave_ticket": slave_ticket,
                        "profit": 0.0
                    }
                }

            close_type = mt5.ORDER_TYPE_SELL if target_pos.type == 0 else mt5.ORDER_TYPE_BUY
            close_price = tick.bid if target_pos.type == 0 else tick.ask

            close_deviation = int(cmd.get("deviation", 20))
            if "BTC" in target_pos.symbol.upper() or "ETH" in target_pos.symbol.upper() or (tick.bid > 1000):
                close_deviation = max(close_deviation, 300)

            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": target_pos.ticket,
                "symbol": target_pos.symbol,
                "volume": target_pos.volume,
                "type": close_type,
                "price": close_price,
                "deviation": close_deviation,
                "magic": target_pos.magic,
                "comment": f"Close C:{master_ticket}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }

            res = mt5.order_send(close_request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                exec_ms = int((time.time() - start_time) * 1000)
                self.logger.info(f"CLOSE SUCCESS Ticket #{target_pos.ticket} in {exec_ms}ms")
                return {
                    "status": "success",
                    "action": "CLOSE",
                    "data": {
                        "master_ticket": master_ticket,
                        "slave_ticket": target_pos.ticket,
                        "profit": target_pos.profit,
                        "execution_ms": exec_ms
                    }
                }
            else:
                err_msg = f"Close failed: retcode={getattr(res, 'retcode', 'N/A')}"
                return {"status": "failed", "action": "CLOSE", "error": err_msg}

        # 3. MODIFY SL/TP
        elif action == "MODIFY_SLTP":
            slave_ticket = cmd.get("slave_ticket")
            master_ticket = cmd.get("master_ticket")

            target_pos = None
            open_positions = mt5.positions_get() or ()
            if slave_ticket:
                target_pos = next((p for p in open_positions if p.ticket == int(slave_ticket)), None)
            if not target_pos and master_ticket:
                tag = f"C:{master_ticket}"
                target_pos = next((p for p in open_positions if tag in p.comment), None)

            if not target_pos:
                return {"status": "failed", "action": "MODIFY_SLTP", "error": "Position not found"}

            mod_request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": target_pos.ticket,
                "symbol": target_pos.symbol,
                "sl": float(cmd.get("sl", 0.0)),
                "tp": float(cmd.get("tp", 0.0))
            }
            res = mt5.order_send(mod_request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                return {"status": "success", "action": "MODIFY_SLTP", "data": {"slave_ticket": target_pos.ticket}}
            return {"status": "failed", "action": "MODIFY_SLTP", "error": f"Modify failed: retcode={getattr(res, 'retcode', 'N/A')}"}

        # 4. PLACE PENDING ORDER
        elif action in ("PLACE_PENDING", "PENDING"):
            master_ticket = cmd.get("master_ticket")
            if master_ticket:
                tag = f"C:{master_ticket}"
                pending_orders = mt5.orders_get() or ()
                existing_ord = next((o for o in pending_orders if tag in o.comment), None)
                if existing_ord:
                    self.logger.warning(
                        f"Pending order with tag '{tag}' already exists on terminal (Ticket #{existing_ord.ticket}). Skipping duplicate."
                    )
                    return {
                        "status": "success",
                        "action": "PLACE_PENDING",
                        "data": {
                            "group_id": cmd.get("group_id"),
                            "master_login": cmd.get("master_login"),
                            "slave_login": self.login_id,
                            "master_ticket": master_ticket,
                            "slave_ticket": existing_ord.ticket,
                            "symbol": existing_ord.symbol,
                            "order_type": cmd.get("order_type"),
                            "master_volume": cmd.get("volume"),
                            "slave_volume": existing_ord.volume_initial,
                            "master_open_price": cmd.get("master_open_price", 0.0),
                            "slave_open_price": existing_ord.price_open,
                            "execution_ms": 0
                        }
                    }
                # Also check if it already triggered and became a position
                open_positions = mt5.positions_get() or ()
                existing_pos = next((p for p in open_positions if tag in p.comment), None)
                if existing_pos:
                    self.logger.warning(
                        f"Order with tag '{tag}' already triggered into position #{existing_pos.ticket}. Skipping duplicate pending."
                    )
                    return {
                        "status": "success",
                        "action": "PLACE_PENDING",
                        "data": {
                            "group_id": cmd.get("group_id"),
                            "master_login": cmd.get("master_login"),
                            "slave_login": self.login_id,
                            "master_ticket": master_ticket,
                            "slave_ticket": existing_pos.ticket,
                            "symbol": existing_pos.symbol,
                            "order_type": cmd.get("order_type"),
                            "master_volume": cmd.get("volume"),
                            "slave_volume": existing_pos.volume,
                            "master_open_price": cmd.get("master_open_price", 0.0),
                            "slave_open_price": existing_pos.price_open,
                            "execution_ms": 0
                        }
                    }

            order_type_str = str(cmd.get("order_type", "BUY_LIMIT")).upper()
            mt5_order_type = ORDER_TYPE_PENDING_MAP.get(order_type_str)
            if mt5_order_type is None:
                try:
                    mt5_order_type = int(cmd.get("order_type"))
                except Exception:
                    return {"status": "failed", "error": f"Invalid pending order type: {order_type_str}"}

            price = float(cmd.get("price", cmd.get("master_open_price", 0.0)))
            digits = getattr(symbol_info, "digits", 5)
            price = round(price, digits)

            # Volume normalization
            req_vol = float(cmd.get("volume", 0.01))
            step = symbol_info.volume_step or 0.01
            norm_vol = max(symbol_info.volume_min, min(symbol_info.volume_max, round(round(req_vol / step) * step, 2)))

            sl = round(float(cmd.get("sl", 0.0)), digits) if float(cmd.get("sl", 0.0)) > 0 else 0.0
            tp = round(float(cmd.get("tp", 0.0)), digits) if float(cmd.get("tp", 0.0)) > 0 else 0.0
            deviation = int(cmd.get("deviation", 20))
            magic = int(cmd.get("magic", 888000))
            comment = str(cmd.get("comment", f"C:{cmd.get('master_ticket', '')}"))
            stoplimit = float(cmd.get("stoplimit", 0.0))

            filling_modes = [getattr(mt5, "ORDER_FILLING_RETURN", 2)]
            f_mode = getattr(symbol_info, "filling_mode", 0)
            if f_mode & 2:
                filling_modes.append(getattr(mt5, "ORDER_FILLING_IOC", 1))
            if f_mode & 1:
                filling_modes.append(getattr(mt5, "ORDER_FILLING_FOK", 0))
            filling_modes = list(dict.fromkeys(filling_modes))

            last_result = None
            for f in filling_modes:
                request = {
                    "action": getattr(mt5, "TRADE_ACTION_PENDING", 5),
                    "symbol": symbol,
                    "volume": norm_vol,
                    "type": mt5_order_type,
                    "price": price,
                    "sl": sl,
                    "tp": tp,
                    "deviation": deviation,
                    "magic": magic,
                    "comment": comment,
                    "type_time": getattr(mt5, "ORDER_TIME_GTC", 0),
                    "type_filling": f
                }
                if stoplimit > 0:
                    request["stoplimit"] = round(stoplimit, digits)

                res = mt5.order_send(request)
                last_result = res
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    exec_ms = int((time.time() - start_time) * 1000)
                    self.logger.info(f"PLACE_PENDING SUCCESS Ticket #{res.order} in {exec_ms}ms")
                    return {
                        "status": "success",
                        "action": "PLACE_PENDING",
                        "data": {
                            "group_id": cmd.get("group_id"),
                            "master_login": cmd.get("master_login"),
                            "slave_login": self.login_id,
                            "master_ticket": cmd.get("master_ticket"),
                            "slave_ticket": res.order,
                            "symbol": symbol,
                            "order_type": order_type_str,
                            "master_volume": cmd.get("volume"),
                            "slave_volume": norm_vol,
                            "master_open_price": cmd.get("master_open_price", 0.0),
                            "slave_open_price": price,
                            "execution_ms": exec_ms
                        }
                    }
                if res and res.retcode != getattr(mt5, "TRADE_RETCODE_INVALID_FILL", 10030):
                    break

            err_msg = f"order_send (pending) failed: retcode={getattr(last_result, 'retcode', 'N/A')}, comment={getattr(last_result, 'comment', 'N/A')}"
            self.logger.error(err_msg)
            return {"status": "failed", "action": "PLACE_PENDING", "error": err_msg}

        # 5. MODIFY PENDING ORDER
        elif action == "MODIFY_PENDING":
            slave_ticket = cmd.get("slave_ticket")
            master_ticket = cmd.get("master_ticket")

            target_order = None
            pending_orders = mt5.orders_get() or ()
            if slave_ticket:
                target_order = next((o for o in pending_orders if o.ticket == int(slave_ticket)), None)
            if not target_order and master_ticket:
                tag = f"C:{master_ticket}"
                target_order = next((o for o in pending_orders if tag in o.comment), None)

            if not target_order:
                return {"status": "failed", "action": "MODIFY_PENDING", "error": "Pending order not found"}

            digits = getattr(symbol_info, "digits", 5)
            new_price = round(float(cmd.get("price", target_order.price_open)), digits)
            new_sl = round(float(cmd.get("sl", target_order.sl)), digits) if float(cmd.get("sl", target_order.sl)) > 0 else 0.0
            new_tp = round(float(cmd.get("tp", target_order.tp)), digits) if float(cmd.get("tp", target_order.tp)) > 0 else 0.0
            new_stoplimit = float(cmd.get("stoplimit", getattr(target_order, "price_stoplimit", 0.0)))

            mod_request = {
                "action": getattr(mt5, "TRADE_ACTION_MODIFY", 3),
                "order": target_order.ticket,
                "price": new_price,
                "sl": new_sl,
                "tp": new_tp,
                "type_time": getattr(mt5, "ORDER_TIME_GTC", 0)
            }
            if new_stoplimit > 0:
                mod_request["stoplimit"] = round(new_stoplimit, digits)

            res = mt5.order_send(mod_request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                return {
                    "status": "success",
                    "action": "MODIFY_PENDING",
                    "data": {
                        "slave_ticket": target_order.ticket,
                        "master_ticket": master_ticket,
                        "price": new_price,
                        "sl": new_sl,
                        "tp": new_tp
                    }
                }
            return {
                "status": "failed",
                "action": "MODIFY_PENDING",
                "error": f"Modify pending failed: retcode={getattr(res, 'retcode', 'N/A')}, comment={getattr(res, 'comment', 'N/A')}"
            }

        # 6. CANCEL PENDING ORDER
        elif action in ("CANCEL_PENDING", "DELETE_PENDING"):
            slave_ticket = cmd.get("slave_ticket")
            master_ticket = cmd.get("master_ticket")

            target_order = None
            pending_orders = mt5.orders_get() or ()
            if slave_ticket:
                target_order = next((o for o in pending_orders if o.ticket == int(slave_ticket)), None)
            if not target_order and master_ticket:
                tag = f"C:{master_ticket}"
                target_order = next((o for o in pending_orders if tag in o.comment), None)

            if not target_order:
                self.logger.warning(
                    f"Pending order for cancel not found (slave: {slave_ticket}, master: {master_ticket}). Already removed."
                )
                return {
                    "status": "success",
                    "action": "CANCEL_PENDING",
                    "data": {
                        "master_ticket": master_ticket,
                        "slave_ticket": slave_ticket
                    }
                }

            cancel_request = {
                "action": getattr(mt5, "TRADE_ACTION_REMOVE", 8),
                "order": target_order.ticket
            }
            res = mt5.order_send(cancel_request)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                exec_ms = int((time.time() - start_time) * 1000)
                self.logger.info(f"CANCEL_PENDING SUCCESS Ticket #{target_order.ticket} in {exec_ms}ms")
                return {
                    "status": "success",
                    "action": "CANCEL_PENDING",
                    "data": {
                        "master_ticket": master_ticket,
                        "slave_ticket": target_order.ticket,
                        "execution_ms": exec_ms
                    }
                }
            else:
                err_msg = f"Cancel pending failed: retcode={getattr(res, 'retcode', 'N/A')}, comment={getattr(res, 'comment', 'N/A')}"
                return {"status": "failed", "action": "CANCEL_PENDING", "error": err_msg}

        return {"status": "failed", "error": f"Unknown action: {action}"}

    def process_command_queue(self):
        """Scans for incoming trade commands from Worker Manager and executes instantly."""
        if not os.path.isdir(self.cmd_dir):
            return False
        executed_any = False
        try:
            with os.scandir(self.cmd_dir) as entries:
                for entry in entries:
                    if not entry.name.endswith(".json") or not entry.is_file():
                        continue
                    fname = entry.name
                    fpath = entry.path
                    cmd_id = fname[:-5]

                    # Check if command was already processed in this worker
                    if cmd_id in self.executed_commands:
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
                        continue

                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            cmd_data = json.load(f)
                        
                        # Execute immediately (< 10ms)!
                        result = self.execute_trade_command(cmd_id, cmd_data)
                        self.executed_commands.add(cmd_id)
                        executed_any = True
                        if len(self.executed_commands) > 1000:
                            self.executed_commands = set(list(self.executed_commands)[-500:])

                        # Write result
                        res_path = os.path.join(self.results_dir, f"{cmd_id}.json")
                        temp_res = f"{res_path}.tmp"
                        with open(temp_res, "w", encoding="utf-8") as f:
                            json.dump(result, f, indent=2)
                        os.replace(temp_res, res_path)

                        # Remove command file
                        try:
                            os.remove(fpath)
                        except Exception:
                            pass
                    except Exception as e:
                        self.logger.error(f"Error processing command {fname}: {e}")
        except Exception:
            pass
        return executed_any

    def monitor_loop(self):
        """High-speed supervision, command execution and telemetry collection loop."""
        self.logger.info("Entering high-speed copier monitor loop...")
        consecutive_failures = 0

        self.launch_mt5()
        self.connect_mt5()

        fast_poll_interval = float(os.environ.get("FAST_POLL_INTERVAL", "0.08"))
        telemetry_interval = float(os.environ.get("TELEMETRY_INTERVAL", "2.0"))
        slave_pos_interval = float(os.environ.get("SLAVE_POS_INTERVAL", "1.0"))
        slave_cmd_interval = float(os.environ.get("SLAVE_CMD_POLL_INTERVAL", "0.12"))
        pos_check_interval = fast_poll_interval if self.is_master else slave_pos_interval
        idle_wait_interval = fast_poll_interval if self.is_master else slave_cmd_interval

        last_telemetry_time = 0
        last_pos_check_time = 0
        last_log_clean_time = 0
        last_minimize_time = 0

        self.logger.info(
            f"Tuning: Role={'MASTER' if self.is_master else 'SLAVE'}, "
            f"PositionScanInterval={pos_check_interval}s, TelemetryInterval={telemetry_interval}s, "
            f"IdleWaitInterval={idle_wait_interval}s"
        )

        while not self.stop_event.is_set():
            did_work = False
            try:
                # 1. Process any pending trade commands INSTANTLY
                did_work = self.process_command_queue()

                now = time.time()
                # 2. Position scanner: ultra-fast (80ms) for Master, conservative (1.0s) for Slave
                if now - last_pos_check_time >= pos_check_interval:
                    self.check_fast_position_changes()
                    last_pos_check_time = now

                # 3. Check connection and full telemetry every telemetry_interval (default 2.0s)
                if now - last_telemetry_time >= telemetry_interval:
                    proc_running = self.is_terminal_running()
                    connected = False

                    if proc_running:
                        connected = self.check_connection()
                        if not connected:
                            try:
                                if mt5 and mt5.terminal_info() is None:
                                    self.logger.warning("MT5 API detached. Reconnecting...")
                                    if self.connect_mt5():
                                        connected = self.check_connection()
                            except Exception:
                                pass

                    if connected:
                        t_info = mt5.terminal_info() if mt5 else None
                        if t_info and not getattr(t_info, "trade_allowed", False):
                            self.ensure_autotrading_enabled()
                        self.collect_telemetry()
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= 15:
                            self.logger.error("Persistent connection failure. Restarting terminal...")
                            self.restart_terminal()
                            consecutive_failures = 0

                    last_telemetry_time = now

                # 4. Periodic log cleanup (every 30 mins)
                if now - last_log_clean_time >= 1800.0:
                    clean_terminal_logs(self.clone_dir, self.logger)
                    last_log_clean_time = now

                # 5. Periodic window minimize check (every 60s) to keep GDI rendering suppressed
                if now - last_minimize_time >= 60.0:
                    self.minimize_terminal_window()
                    last_minimize_time = now

            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")

            # If commands were just executed, loop immediately with zero sleep to handle bursts.
            # Otherwise, sleep idle_wait_interval (80ms for master, 120ms for slave) to keep CPU load low.
            if did_work:
                self.stop_event.wait(0.001)
            else:
                self.stop_event.wait(idle_wait_interval)

        # Cleanup on stop
        self.logger.info("Stopping worker...")
        if mt5:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.kill_process()
        self.logger.info("Worker stopped.")

    def restart_terminal(self):
        self.logger.info("Restarting MT5 terminal...")
        if mt5:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.kill_process()
        time.sleep(2)
        if self.launch_mt5():
            self.connect_mt5()

    def start(self):
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dedicated MT5 Account Worker")
    parser.add_argument("--login", required=True, help="MT5 login ID")
    parser.add_argument("--password", required=True, help="MT5 password")
    parser.add_argument("--server", required=True, help="MT5 broker server")
    parser.add_argument("--terminal-path", required=True, help="Master terminal template path")
    parser.add_argument("--clone-dir", required=True, help="Folder for this cloned instance")
    parser.add_argument("--config-template", required=True, help="Path to config.ini template")
    parser.add_argument("--interval", type=int, default=5, help="Telemetry poll interval in seconds")
    parser.add_argument("--expert", default="", help="EA Expert name")
    parser.add_argument("--symbol", default="XAUUSD", help="Symbol")
    parser.add_argument("--timeframe", default="M1", help="Timeframe")
    parser.add_argument("--is-master", action="store_true", help="Flag if this terminal is a copy trading master")

    args = parser.parse_args()

    worker = MT5Worker(
        login_id=args.login,
        password=args.password,
        server=args.server,
        terminal_path=args.terminal_path,
        clone_dir=args.clone_dir,
        config_template_path=args.config_template,
        sync_interval=args.interval,
        expert=args.expert,
        symbol=args.symbol,
        timeframe=args.timeframe,
        is_master=args.is_master
    )

    worker.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping worker...")
        worker.stop()
        print("Worker stopped.")
