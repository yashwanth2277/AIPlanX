import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

STORE_BACKEND = os.getenv("AIPlanX_STORE", "sqlite").strip().lower()
SQLITE_PATH = Path(os.getenv("SQLITE_PATH", str(ROOT / "aiplanx.db")))
if not SQLITE_PATH.is_absolute():
    SQLITE_PATH = ROOT / SQLITE_PATH

SESSION_DIR = Path(os.getenv("SESSION_DIR", str(ROOT / "management_sessions")))
if not SESSION_DIR.is_absolute():
    SESSION_DIR = ROOT / SESSION_DIR

REPORT_PATH = Path(os.getenv("REPORT_PATH", str(ROOT / "final_report.json")))
if not REPORT_PATH.is_absolute():
    REPORT_PATH = ROOT / REPORT_PATH

EMPLOYEE_PATH = Path(os.getenv("EMPLOYEE_PATH", str(ROOT / "employees.csv")))
if not EMPLOYEE_PATH.is_absolute():
    EMPLOYEE_PATH = ROOT / EMPLOYEE_PATH

JSON_PROJECTS_DIR = ROOT / "json_projects"
TEAM_WORKFLOW_PATH = ROOT / "team_workflow.json"
