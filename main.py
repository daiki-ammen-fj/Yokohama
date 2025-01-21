#!python3.11
# main.py

import logging
import sys
import argparse
import os
import subprocess  
from step1_connect import check_device_connection
from step2_DUT_setup import setup_dut

# Device credentials
DEVICE_CREDENTIALS = {
    "Spectrum_Analyzer_N9040B": {"ip": "10.18.180.47"},
    "Signal Generator_M9384B": {"ip": "10.18.180.48"},
    "DU_Emulator_S5040A": {"ip": "10.18.180.152"},
    "DUT_ZCU670": {"ip": "10.18.180.151", "user": "petalinux", "password": "petalinux00", "sudo_password": "petalinux00"},
}

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("script_log.log", mode='w', encoding='utf-8')
    ]
)

# Argument parser
parser = argparse.ArgumentParser(description='Debug arguments')
parser.add_argument('-b', '--batch', help='Batch script path', default=os.getenv("BATCH_SCRIPT_PATH", r"C:\Users\labuser\qlight-control\run_qlight_check.bat"))
parser.add_argument('-p', '--paam', help='PAAM script path', default=os.getenv("PAAM_SCRIPT_PATH", r"C:\Users\labuser\pybeacon\run_paam_dl_reg.bat"))
parser.add_argument('--debug', action='store_true', help='Enable debug mode')
args = parser.parse_args()

def is_debug_mode():
    """Check if the script is running in debug mode."""
    debug_mode = os.getenv('DEBUG', 'False') == 'True' or args.debug
    logging.info(f"Debug mode is {'enabled' if debug_mode else 'disabled'}")
    return debug_mode

def initialize():
    """Initialization process."""
    try:
        debug_mode = is_debug_mode()

        # Step 1: Check device connection
        logging.info("Proceeding to Step 1...")
        for device, credentials in DEVICE_CREDENTIALS.items():
            device_ip = credentials["ip"]
            if not check_device_connection(device_ip):
                logging.error(f"Initialization failed: {device} ({device_ip}) is not reachable.")
                return

        # Step 2: Setup DUT using credentials
        logging.info("Proceeding to Step 2...")
        dut_credentials = DEVICE_CREDENTIALS.get("DUT_ZCU670")
        if dut_credentials:
            user = dut_credentials["user"]
            password = dut_credentials["password"]
            sudo_password = dut_credentials["sudo_password"]
            setup_dut(dut_credentials["ip"], user, password, sudo_password)

    except Exception as e:
        logging.error(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        initialize()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
