import sqlite3
import subprocess
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

# ⚠️ Optional: Replace with your actual Discord Webhook URL if using notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1546731209332363345/nv6Muy5o_Lc6EL0z5PBrmkBytDe-u8qJld6cQPPqOGnc_5fLXjN1GVGOM9kMSaZG1Ns9"

app = FastAPI(title="Self-Healing Infrastructure Engine")

class CrashAlert(BaseModel):
    service_name: str
    error_code: str
    stack_trace: str

def save_log_to_db(service: str, error: str, action: str):
    conn = sqlite3.connect("healing.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO incident_logs (service_name, error_code, action_taken) VALUES (?, ?, ?);",
        (service, error, action)
    )
    conn.commit()
    conn.close()

def execute_remediation(service: str, action: str):
    """Executes actual system commands via Python's subprocess module."""
    print(f"\n[SUBPROCESS WORKER] Initiating action '{action}' for service '{service}'...")

    # Map engine decisions to real system commands
    if action == "flush_redis_cache":
        # Example 1: PowerShell command (e.g., echo log entry or clear temporary files)
        cmd = ["powershell", "-Command", f"Write-Output 'Flushing cache for {service}...'; Get-Date"]

    elif action == "restart_container":
        # Example 2: Docker command (e.g., restart container named after service)
        cmd = ["docker", "restart", service]

    else:
        # Fallback command
        cmd = ["powershell", "-Command", f"Write-Output 'Executing fallback remediation for {service}'"]

    try:
        # Run command synchronously inside the background task worker
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,    # Kills process if hanging longer than 15s
            check=True     # Raises CalledProcessError if return code != 0
        )
        
        print(f"[SUBPROCESS WORKER] Command Output:\n{result.stdout.strip()}")
        print(f"[SUBPROCESS WORKER] Successfully executed '{action}' for '{service}'.\n")

    except subprocess.CalledProcessError as e:
        print(f"[SUBPROCESS WORKER] ERROR executing command for {service}!")
        print(f"Exit Code: {e.returncode}")
        print(f"Stderr: {e.stderr.strip()}")

    except subprocess.TimeoutExpired:
        print(f"[SUBPROCESS WORKER] TIMEOUT: Command execution for {service} exceeded 15 seconds.")

    except Exception as e:
        print(f"[SUBPROCESS WORKER] Unexpected execution error: {e}")

@app.post("/webhook/incident")
def handle_incident(alert: CrashAlert, background_tasks: BackgroundTasks):
    full_text = f"{alert.error_code} {alert.stack_trace}".upper()
    
    if "OOM" in full_text or "MEMORY" in full_text:
        recommended_action = "flush_redis_cache"
    else:
        recommended_action = "restart_container"

    # 1. Log to SQLite
    save_log_to_db(alert.service_name, alert.error_code, recommended_action)

    # 2. Trigger non-blocking subprocess execution
    background_tasks.add_task(execute_remediation, alert.service_name, recommended_action)

    return {
        "status": "PROCESSED",
        "service": alert.service_name,
        "action_taken": recommended_action,
        "dispatch_status": "EXECUTING_SUBPROCESS_IN_BACKGROUND"
    }

@app.get("/incidents")
def get_incidents():
    conn = sqlite3.connect("healing.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, service_name, error_code, action_taken, timestamp FROM incident_logs ORDER BY timestamp DESC;")
    rows = cursor.fetchall()
    conn.close()

    incidents = [dict(row) for row in rows]
    return {
        "total_incidents": len(incidents),
        "incidents": incidents
    }