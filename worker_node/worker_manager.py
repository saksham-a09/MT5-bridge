#!/usr/bin/env python3
import os
import sys
import json
import time
import signal
import platform
import argparse
import subprocess
import threading
import psutil
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def load_dotenv(dotenv_path=".env"):
    if not os.path.exists(dotenv_path):
        return False
    with open(dotenv_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v = v[1:-1]
                os.environ.setdefault(k, v)
    return True

def is_wine():
    import ctypes
    try:
        return hasattr(ctypes.windll.ntdll, 'wine_get_version')
    except Exception:
        pass
    for env_var in ["WINEPREFIX", "WINELOADERNOEXEC", "WINEARCH"]:
        if env_var in os.environ:
            return True
    return False

def trim_working_set(pid=None):
    """Trims unused working set memory pages on Windows to minimize physical RAM footprint."""
    if os.name != "nt" or is_wine():
        return
    try:
        import ctypes
        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_SET_QUOTA = 0x0100
        target_pid = pid or os.getpid()
        h_proc = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, target_pid)
        if h_proc:
            ctypes.windll.psapi.EmptyWorkingSet(h_proc)
            ctypes.windll.kernel32.CloseHandle(h_proc)
    except Exception:
        pass

def api_request(method, url, data=None, headers=None, timeout=10):
    # Avoid Windows IPv6 DNS resolution lag/timeout on localhost
    if "://localhost:" in url:
        url = url.replace("://localhost:", "://127.0.0.1:")
    elif "://localhost/" in url:
        url = url.replace("://localhost/", "://127.0.0.1/")

    req_headers = {"Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = Request(url, data=payload, headers=req_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            res = json.loads(err_body)
            if isinstance(res, dict):
                res["status_code"] = e.code
            return res
        except Exception:
            return {"success": False, "error": f"HTTP {e.code}: {err_body}", "status_code": e.code}
    except Exception as e:
        return {"success": False, "error": str(e)}

class WorkerManager:
    def __init__(self, hub_url, node_id, node_name, api_key, master_mt5, clients_dir,
                 max_terminals=25, poll_interval=8, heartbeat_interval=10):
        self.hub_url = hub_url.rstrip("/")
        self.node_id = node_id
        self.node_name = node_name
        self.api_key = api_key
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.master_mt5 = os.path.abspath(os.path.normpath(master_mt5))
        self.clients_dir = os.path.abspath(os.path.normpath(clients_dir))
        self.template_path = os.path.abspath(os.path.join(self.script_dir, "example.ini"))
        self.max_terminals = max_terminals
        self.poll_interval = poll_interval
        self.heartbeat_interval = heartbeat_interval
        
        self.running_workers = {}  # login_id -> { "process": Popen, "config": dict, "dir": str }
        self.dispatched_cmd_ids = set()  # Track dispatched command IDs to prevent duplicate execution
        self.is_running = True

        os.makedirs(self.clients_dir, exist_ok=True)

    def log(self, msg, level="INFO"):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [{level}] [Node {self.node_id}] {msg}")

    def kill_processes_for_login(self, login_id):
        """Kills any python worker or MT5 terminal process for a given login ID."""
        terminated = 0
        login_id_str = str(login_id)
        my_pid = os.getpid()

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']
                if pid == my_pid:
                    continue
                name = (proc.info.get('name') or '').lower()
                cmdline = proc.info.get('cmdline') or []
                cmdline_str = " ".join(cmdline).lower()

                is_worker = "worker.py" in cmdline_str and f"--login {login_id_str}" in cmdline_str
                is_terminal = ("terminal" in name or "wine" in name) and f"clone_{login_id_str}" in cmdline_str

                if is_worker or is_terminal:
                    proc.kill()
                    terminated += 1
            except Exception:
                pass
        return terminated

    def global_cleanup(self):
        """Clean up any orphan terminals or workers in clients_dir on startup."""
        self.log("Performing startup cleanup of stale workers/terminals...")
        clients_name = os.path.basename(self.clients_dir).lower()
        my_pid = os.getpid()
        count = 0

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['pid'] == my_pid:
                    continue
                name = (proc.info.get('name') or '').lower()
                cmdline = proc.info.get('cmdline') or []
                cmdline_str = " ".join(cmdline).lower()

                if clients_name in cmdline_str or "worker.py" in cmdline_str:
                    if "terminal" in name or "wine" in name or "python" in name:
                        proc.kill()
                        count += 1
            except Exception:
                pass
        if count > 0:
            self.log(f"Cleaned up {count} existing process(es).")

    def register(self, max_retries=10, retry_delay=2):
        """Registers this hardware node with the Central Hub with retry attempts."""
        self.log(f"Connecting to Central Hub at {self.hub_url}...")
        vm = psutil.virtual_memory()
        os_desc = f"{platform.system()} {platform.release()} ({psutil.cpu_count(logical=True)} vCPUs, {round(vm.total / (1024**3), 1)}GB RAM)"
        if is_wine():
            os_desc += " [Wine]"

        payload = {
            "node_id": self.node_id,
            "name": self.node_name,
            "api_key": self.api_key,
            "max_terminals": self.max_terminals,
            "os_info": os_desc
        }

        for attempt in range(1, max_retries + 1):
            res = api_request("POST", f"{self.hub_url}/api/nodes/register", data=payload, timeout=5)
            if res.get("success"):
                self.log(f"Successfully registered node '{self.node_name}' (ID: {self.node_id}).")
                return True
            else:
                err = res.get("error") or res.get("message") or "Hub unreachable"
                if attempt < max_retries:
                    self.log(f"Hub not ready yet (attempt {attempt}/{max_retries}: {err}). Retrying in {retry_delay}s...", level="WARNING")
                    time.sleep(retry_delay)
                else:
                    self.log(f"Could not reach Hub after {max_retries} attempts: {err}. Proceeding in background.", level="WARNING")
        return False

    def send_heartbeat(self):
        """Sends hardware telemetry to the Central Hub."""
        vm = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)
        payload = {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(vm.percent, 1),
            "ram_used_mb": round(vm.used / (1024**2), 1),
            "ram_total_mb": round(vm.total / (1024**2), 1),
            "active_terminals": len(self.running_workers)
        }
        headers = {"x-node-api-key": self.api_key}
        res = api_request("POST", f"{self.hub_url}/api/nodes/{self.node_id}/heartbeat", data=payload, headers=headers)
        if isinstance(res, dict) and (res.get("status_code") == 404 or "not registered" in str(res).lower()):
            self.log("Node not registered in Hub yet. Re-registering...", level="INFO")
            self.register(max_retries=1)

    def spawn_worker(self, login, creds):
        """Spawns an isolated worker subprocess for an assigned MT5 account."""
        login_str = str(login)
        clone_dir = os.path.abspath(os.path.join(self.clients_dir, f"clone_{login_str}"))
        worker_script = os.path.abspath(os.path.join(self.script_dir, "worker.py"))
        terminal_exe = os.path.abspath(os.path.join(self.master_mt5, "terminal64.exe"))
        if not os.path.isfile(terminal_exe):
            terminal_exe = os.path.abspath(os.path.join(self.master_mt5, "terminal.exe"))

        os.makedirs(clone_dir, exist_ok=True)
        log_path = os.path.join(clone_dir, f"worker_{login_str}_stdout.log")

        cmd = [
            sys.executable,
            "-O",
            worker_script,
            "--login", login_str,
            "--password", str(creds["password"]),
            "--server", str(creds["server"]),
            "--terminal-path", terminal_exe,
            "--clone-dir", clone_dir,
            "--config-template", self.template_path,
            "--interval", "4"
        ]

        if creds.get("expert"):
            cmd.extend(["--expert", creds["expert"]])
        if creds.get("symbol"):
            cmd.extend(["--symbol", creds["symbol"]])
        if creds.get("timeframe"):
            cmd.extend(["--timeframe", creds["timeframe"]])

        creation_flags = 0
        if os.name == "nt" and not is_wine():
            creation_flags = subprocess.DETACHED_PROCESS

        self.log(f"Spawning MT5 Worker for Login {login_str} ({creds['server']})...")
        try:
            log_file = open(log_path, "a", encoding="utf-8")
            log_file.write(f"\n--- Spawning at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            log_file.flush()

            proc = subprocess.Popen(
                cmd,
                cwd=self.script_dir,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=log_file,
                creationflags=creation_flags
            )
            log_file.close()
            return proc, clone_dir
        except Exception as e:
            self.log(f"Failed to spawn worker for {login_str}: {e}", level="ERROR")
            return None, clone_dir

    def sync_accounts(self):
        """Polls assigned accounts from Central Hub and starts/stops workers accordingly."""
        headers = {"x-node-api-key": self.api_key}
        res = api_request("GET", f"{self.hub_url}/api/nodes/{self.node_id}/accounts", headers=headers)
        if not res.get("success"):
            return

        assigned_accounts = res.get("accounts", [])
        active_map = {}

        for acc in assigned_accounts:
            login = int(acc["login"])
            status = acc.get("status", "active")
            if status == "active":
                active_map[login] = acc

        # 1. Start or update active accounts
        for login, creds in active_map.items():
            if login not in self.running_workers:
                proc, cdir = self.spawn_worker(login, creds)
                if proc:
                    self.running_workers[login] = {
                        "process": proc,
                        "config": creds,
                        "dir": cdir
                    }
                    time.sleep(2)  # Stagger worker spawns
            else:
                tracked = self.running_workers[login]
                proc = tracked["process"]
                old_cfg = tracked["config"]

                # Detect config changes
                cfg_changed = (
                    creds.get("password") != old_cfg.get("password") or
                    creds.get("server") != old_cfg.get("server") or
                    creds.get("expert") != old_cfg.get("expert") or
                    creds.get("symbol") != old_cfg.get("symbol")
                )

                if cfg_changed:
                    self.log(f"Credentials changed for Login {login}. Restarting worker...")
                    self.kill_processes_for_login(login)
                    new_proc, cdir = self.spawn_worker(login, creds)
                    self.running_workers[login] = {
                        "process": new_proc,
                        "config": creds,
                        "dir": cdir
                    }
                    time.sleep(2)
                elif proc.poll() is not None:
                    self.log(f"Worker for Login {login} exited unexpectedly (code {proc.returncode}). Restarting...", level="WARNING")
                    self.kill_processes_for_login(login)
                    new_proc, cdir = self.spawn_worker(login, creds)
                    self.running_workers[login]["process"] = new_proc
                    time.sleep(2)

        # 2. Terminate removed or stopped accounts
        for login in list(self.running_workers.keys()):
            if login not in active_map:
                self.log(f"Account {login} stopped or unassigned. Shutting down worker...")
                self.kill_processes_for_login(login)
                del self.running_workers[login]

    def report_telemetry(self):
        """Reads telemetry.json from each worker clone directory and batches to Hub."""
        batch = []
        for login, info in self.running_workers.items():
            t_file = os.path.join(info["dir"], "telemetry.json")
            if os.path.isfile(t_file):
                try:
                    with open(t_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    batch.append(data)
                except Exception:
                    pass

        if batch:
            headers = {"x-node-api-key": self.api_key}
            res = api_request("POST", f"{self.hub_url}/api/nodes/{self.node_id}/telemetry", data={"terminals": batch}, headers=headers)
            if isinstance(res, dict) and res.get("commands"):
                self.dispatch_commands(res["commands"])

    def check_and_report_urgent_telemetry(self):
        """High-frequency scanner that catches urgent master trade events and pushes to Hub instantly."""
        urgent_batch = []
        for login, info in list(self.running_workers.items()):
            u_file = os.path.join(info["dir"], "urgent_telemetry.json")
            if os.path.isfile(u_file):
                try:
                    with open(u_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    urgent_batch.append(data)
                    os.remove(u_file)
                except Exception:
                    pass

        if urgent_batch:
            headers = {"x-node-api-key": self.api_key}
            res = api_request("POST", f"{self.hub_url}/api/nodes/{self.node_id}/telemetry", data={"terminals": urgent_batch}, headers=headers, timeout=2)
            if isinstance(res, dict) and res.get("commands"):
                self.dispatch_commands(res["commands"])

    def dispatch_commands(self, commands):
        """Writes command files to target worker directories for instant execution."""
        if not commands:
            return
        for cmd in commands:
            cmd_id = cmd["id"]
            if cmd_id in self.dispatched_cmd_ids:
                continue

            login = cmd["login"]
            target_clone = os.path.join(self.clients_dir, f"clone_{login}")
            target_cmd_dir = os.path.join(target_clone, "commands")
            if os.path.isdir(target_cmd_dir):
                cmd_file = os.path.join(target_cmd_dir, f"{cmd_id}.json")
                temp_file = f"{cmd_file}.tmp"
                payload = cmd.get("payload", {})
                payload["action"] = cmd.get("action")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                os.replace(temp_file, cmd_file)
                self.dispatched_cmd_ids.add(cmd_id)
                if len(self.dispatched_cmd_ids) > 1000:
                    self.dispatched_cmd_ids = set(list(self.dispatched_cmd_ids)[-500:])
                self.log(f"Fast-path dispatched command {cmd_id} ({cmd.get('action')}) to Worker {login}.")

    def poll_and_dispatch_commands(self):
        """Fallback polling for pending trade commands from Central Hub."""
        headers = {"x-node-api-key": self.api_key}
        res = api_request("GET", f"{self.hub_url}/api/nodes/{self.node_id}/commands", headers=headers, timeout=2)
        commands = res.get("commands", []) if isinstance(res, dict) else []
        self.dispatch_commands(commands)

    def collect_and_report_results(self):
        """Scans for execution results written by workers and submits them to Central Hub."""
        headers = {"x-node-api-key": self.api_key}
        for login, info in list(self.running_workers.items()):
            results_dir = os.path.join(info["dir"], "results")
            if not os.path.isdir(results_dir):
                continue
            try:
                for fname in os.listdir(results_dir):
                    if not fname.endswith(".json"):
                        continue
                    rpath = os.path.join(results_dir, fname)
                    cmd_id = fname[:-5]
                    try:
                        with open(rpath, "r", encoding="utf-8") as f:
                            res_data = json.load(f)
                        api_request(
                            "POST",
                            f"{self.hub_url}/api/nodes/{self.node_id}/commands/{cmd_id}/result",
                            data=res_data,
                            headers=headers,
                            timeout=3
                        )
                        os.remove(rpath)
                        self.log(f"Reported execution result for command {cmd_id} (Status: {res_data.get('status')}).")
                    except Exception as e:
                        self.log(f"Error submitting result for {cmd_id}: {e}", level="WARNING")
            except Exception:
                pass

    def run(self):
        self.log("=" * 60)
        self.log(f"Starting Worker Manager Daemon on {self.node_id} ({self.node_name})")
        self.log(f"  Central Hub:    {self.hub_url}")
        self.log(f"  Master MT5:     {self.master_mt5}")
        self.log(f"  Clients Dir:    {self.clients_dir}")
        self.log(f"  Terminal Limit: {self.max_terminals}")
        self.log("=" * 60)

        self.global_cleanup()
        self.register()

        last_hb = 0
        last_poll = 0
        last_telemetry = 0
        last_cmd_poll = 0
        last_mem_trim = 0

        while self.is_running:
            now = time.time()

            # 1. High-speed check for urgent position changes from workers (< 10ms)
            self.check_and_report_urgent_telemetry()

            # 2. Check and report execution results from workers (< 10ms)
            self.collect_and_report_results()

            # 3. High-speed fallback command poll (every 50ms)
            if now - last_cmd_poll >= 0.05:
                try:
                    self.poll_and_dispatch_commands()
                except Exception:
                    pass
                last_cmd_poll = now

            # 4. Heartbeat
            if now - last_hb >= self.heartbeat_interval:
                try:
                    self.send_heartbeat()
                except Exception as e:
                    self.log(f"Heartbeat failed: {e}", level="WARNING")
                last_hb = now

            # 5. Accounts Sync
            if now - last_poll >= self.poll_interval:
                try:
                    self.sync_accounts()
                except Exception as e:
                    self.log(f"Account sync error: {e}", level="ERROR")
                last_poll = now

            # 6. Full Routine Telemetry Reporting (every 1s)
            if now - last_telemetry >= 1.0:
                try:
                    self.report_telemetry()
                except Exception as e:
                    pass
                last_telemetry = now

            # 7. Periodic working set memory trim across manager and workers (every 60s)
            if now - last_mem_trim >= 60.0:
                trim_working_set(os.getpid())
                for login, info in list(self.running_workers.items()):
                    proc = info.get("process")
                    if proc and proc.pid:
                        trim_working_set(proc.pid)
                try:
                    import gc
                    gc.collect()
                except Exception:
                    pass
                last_mem_trim = now

            time.sleep(0.02)

        self.shutdown()

    def shutdown(self):
        self.log("Shutdown requested. Terminating all running workers and terminals...")
        for login in list(self.running_workers.keys()):
            self.kill_processes_for_login(login)
        self.log("Shutdown complete.")


def handle_exit(signum, frame):
    global manager
    if manager:
        manager.is_running = False

manager = None

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(os.path.join(script_dir, ".env"))

    parser = argparse.ArgumentParser(description="Distributed MT5 Worker Manager Node")
    parser.add_argument("--hub-url", default=os.getenv("HUB_URL", "http://127.0.0.1:8000"), help="Central Hub URL")
    parser.add_argument("--node-id", default=os.getenv("NODE_ID", "local-node-1"), help="Unique Node ID")
    parser.add_argument("--node-name", default=os.getenv("NODE_NAME", "Primary Local Node"), help="Friendly node name")
    parser.add_argument("--api-key", default=os.getenv("NODE_API_KEY", "local_secret_key"), help="Node secret API key")
    parser.add_argument("--master-mt5", default=os.getenv("MASTER_MT5_DIR", r"E:\MT5 instances\Master MT5"), help="Master MT5 template folder")
    parser.add_argument("--clients-dir", default=os.getenv("CLIENTS_DIR", os.path.join(script_dir, "CLIENTS")), help="Folder for clones")
    parser.add_argument("--max-terminals", type=int, default=int(os.getenv("MAX_TERMINALS", "25")), help="Capacity limit")
    parser.add_argument("--poll-interval", type=int, default=int(os.getenv("POLL_INTERVAL", "8")), help="Poll interval in seconds")

    args = parser.parse_args()

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    manager = WorkerManager(
        hub_url=args.hub_url,
        node_id=args.node_id,
        node_name=args.node_name,
        api_key=args.api_key,
        master_mt5=args.master_mt5,
        clients_dir=args.clients_dir,
        max_terminals=args.max_terminals,
        poll_interval=args.poll_interval
    )

    manager.run()
