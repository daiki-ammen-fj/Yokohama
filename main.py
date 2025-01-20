#main.py
#!python3.11
# main.py

import logging
import sys
import argparse
import os
import subprocess  # 追加
from step1_connect import check_device_connection 
from step2_run_batch import run_batch_script
from step3_ngp800 import control_ngp800
from step4_run_paam import run_paam_script
from step5_psg import configure_keysight_psg
from step6_smw200a import configure_r_and_s_smw200a
from step7_spectrum_analyzer import connect_spectrum_analyzer

# Device credentials
DEVICE_CREDENTIALS = {
    "RS_ngp800": {"ip": "172.22.2.12"},
    "RS_spectrum_analyzer": {"ip": "172.22.0.70", "tcpip": "172.22.0.70::5025"},
    "keysight_psg": {"ip": "172.22.2.31", "tcpip": "172.22.2.31::hislip200"},
    "RS_signal_generator_smw200a": {"ip": "172.22.2.23", "tcpip": "172.22.2.23::5025"},
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

def run_measurement():
    """Run the measurement.py script and prompt for re-execution."""
    try:
        measurement_script_path = os.path.join("measurement_module", "measurement.py")
        if not os.path.exists(measurement_script_path):
            logging.error(f"Measurement script not found at {measurement_script_path}. Exiting.")
            sys.exit(1)

        while True:
            logging.info("Running measurement script...")
            result = subprocess.run([sys.executable, measurement_script_path], capture_output=True, text=True)

            if result.returncode == 0:
                logging.info("Measurement script completed successfully.")
                logging.info(result.stdout)
            else:
                logging.error("Measurement script failed.")
                logging.error(result.stderr)

            # Ask the user whether to run the script again
            user_input = input("Do you want to run the measurement script again? (yes/no): ").strip().lower()
            if user_input not in ['yes', 'y']:
                logging.info("Exiting measurement script loop.")
                break

    except Exception as e:
        logging.error(f"Failed to execute measurement script: {e}", exc_info=True)
        sys.exit(1)

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

        # Step 2: Run the batch script
        logging.info("Proceeding to Step 2...")
        if not run_batch_script(args.batch):
            logging.error("Batch script failed. Exiting initialization.")
            return

        # Step 3: Test NGP800 connection
        logging.info("Proceeding to Step 3...")
        control_ngp800(DEVICE_CREDENTIALS["RS_ngp800"]["ip"], debug_mode)

        # Step 4: Run PAAM script
        logging.info("Proceeding to Step 4...")
        run_paam_script(args.paam, debug_mode)

        # Step 5: Configure Keysight PSG
        logging.info("Proceeding to Step 5...")
        configure_keysight_psg(DEVICE_CREDENTIALS["keysight_psg"]["ip"], debug_mode)

        # Step 6: Configure R&S SMW200A
        logging.info("Proceeding to Step 6...")
        configure_r_and_s_smw200a(DEVICE_CREDENTIALS["RS_signal_generator_smw200a"]["ip"], debug_mode)

        # Step 7: Connect Spectrum Analyzer
        logging.info("Proceeding to Step 7...")
        if connect_spectrum_analyzer(DEVICE_CREDENTIALS["RS_spectrum_analyzer"]["ip"], debug_mode):
            # Step 8: Run measurement script if Step 7 succeeds
            run_measurement()
        else:
            logging.error("Step 7 failed. Measurement script will not be executed.")
            sys.exit(1)

    except Exception as e:
        logging.error(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        initialize()
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
