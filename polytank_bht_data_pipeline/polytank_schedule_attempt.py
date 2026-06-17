import schedule
import time
from datetime import datetime, timedelta
import subprocess
import threading
import logging
import sys
import os

# Select date here
today = datetime.today()
yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
chosen_date = today.strftime("%Y-%m-%d")


# ========== CONFIGURATION - MODIFY THESE ==========
# Set your date range here (will be overridden by command line args if provided)
START_DATE = "2026-01-23"  # Change this
END_DATE = "2026-01-23"     # Change this

FIELDS = ["recruit_profile", "tank_social", "brand_aware", "brand_impress", "media", "tank_preference", ] #  

# =================================================
# TIMEOUT & DELAY SETTINGS
TASK_TIMEOUT = 600  # 10 minutes per task
DELAY_BETWEEN_TASKS = 30  # 20 seconds between tasks (API gateway protection)

# Fix Unicode encoding for Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

log_filename = f"scheduler_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def run_task(field, start_date, end_date):
    """Run single task for a field"""
    command = [
        sys.executable, 
        "main_argparse.py", 
        "-f", field, 
        "-s", start_date,
        "-e", end_date
    ]
    logging.info(f"Starting: {field} (timeout: {TASK_TIMEOUT}s)")
    start_time = datetime.now()
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, 
                              check=True, timeout=TASK_TIMEOUT)
        duration = (datetime.now() - start_time).total_seconds()
        logging.info(f"SUCCESS: {field} ({duration:.1f}s)")
        if result.stdout.strip():
            logging.debug(f"STDOUT {field}: {result.stdout.strip()}")
    except subprocess.TimeoutExpired:
        duration = (datetime.now() - start_time).total_seconds()
        logging.error(f"TIMEOUT: {field} after {duration:.1f}s")
    except subprocess.CalledProcessError as e:
        duration = (datetime.now() - start_time).total_seconds()
        logging.error(f"FAILED: {field} in {duration:.1f}s (code: {e.returncode})")
        if e.stderr:
            logging.error(f"STDERR: {e.stderr[:500]}...")
    except Exception as e:
        logging.error(f"ERROR {field}: {str(e)}")

def main():
    start_time = datetime.now()
    logging.info(f"Scheduler started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get dates
    if len(sys.argv) >= 3:
        start_date, end_date = sys.argv[1], sys.argv[2]
    else:
        start_date, end_date = START_DATE, END_DATE
    
    logging.info(f"Dates: {start_date} -> {end_date}")
    logging.info(f"Fields: {', '.join(FIELDS)}")
    logging.info(f"Task timeout: {TASK_TIMEOUT}s, Delay between tasks: {DELAY_BETWEEN_TASKS}s")
    
    # Run tasks SEQUENTIALLY with 20-second delays
    for i, field in enumerate(FIELDS):
        if i > 0:  # Skip delay before first task
            logging.info(f"Waiting {DELAY_BETWEEN_TASKS}s before next task...")
            time.sleep(DELAY_BETWEEN_TASKS)
        
        run_task(field, start_date, end_date)
    
    total_duration = (datetime.now() - start_time).total_seconds()
    logging.info(f"All tasks completed in {total_duration:.1f}s")

if __name__ == "__main__":
    main()