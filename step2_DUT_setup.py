#!python3.11
# step2_DUT_setup.py

import paramiko
import serial
import time
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def create_ssh_client(ip, user, password):
    """SSHクライアントを作成して接続する"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 未知のホストキーを自動的に追加
        client.connect(ip, username=user, password=password)
        logging.info(f"Connected to {ip} via SSH")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to {ip}: {e}")
        return None

def execute_ssh_command(client, command, sudo_password=None, debug=False):
    """SSHでコマンドを実行"""
    try:
        if sudo_password and "sudo" in command:
            if debug:
                logging.info(f"Sending password for sudo authentication: {sudo_password}")  # デバッグモードでパスワードを表示
            command = f"sudo -S {command}"

        stdin, stdout, stderr = client.exec_command(command)
        
        if sudo_password and "sudo" in command:
            logging.debug(f"Sending sudo password: {sudo_password}")  # デバッグ用にパスワードを確認（本番環境では削除）
            stdin.write(f"{sudo_password}\n")  # sudoのパスワードを渡す
            stdin.flush()
        
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if output:
            logging.info(f"SSH Command Output: {output}")
        if error:
            logging.error(f"SSH Command Error: {error}")
        return output, error
    except Exception as e:
        logging.error(f"Failed to execute SSH command {command}: {e}")
        return None, str(e)

def execute_serial_command(serial_conn, command, wait_time=1):
    """シリアル接続でコマンドを実行"""
    try:
        serial_conn.write((command + "\n").encode())
        time.sleep(wait_time)
        output = serial_conn.read_all().decode().strip()
        if output:
            logging.info(f"Serial Command Output: {output}")
        return output
    except Exception as e:
        logging.error(f"Failed to execute serial command {command}: {e}")
        return None

def setup_dut_via_ssh(ip, user, password, sudo_password, debug=False):
    """SSHでDUTを設定"""
    client = create_ssh_client(ip, user, password)
    if not client:
        logging.error(f"Failed to connect to DUT {ip} via SSH.")
        return


    try:
        # カーネル起動後のログイン処理
        logging.info("Logging into DUT after kernel boot...")
        transport = client.get_transport()
        channel = transport.open_session()
        channel.get_pty()
        channel.invoke_shell()

        # ログインプロンプトの処理
        while True:
            time.sleep(1)
            if channel.recv_ready():
                output = channel.recv(1024).decode("utf-8")
                logging.info(f"Received: {output.strip()}")
                if "login:" in output:
                    channel.send(user + "\n")
                elif "Password:" in output:
                    channel.send(password + "\n")
                elif "$" in output or "#" in output:  # ログイン成功を確認
                    logging.info("Login successful.")
                    break

        # `ru-controller`の確認
        logging.info("Checking if ru-controller is already running...")
        channel.send("ps aux | grep ru-controller\n")
        time.sleep(1)
        if channel.recv_ready():
            output = channel.recv(1024).decode("utf-8")
            if "PLL Sync state 0xdd Locked" in output:
                logging.info("PLL Sync state 0xdd Locked detected, skipping ru-controller execution.")
                return

        # `sudo su`で昇格してru-controllerを実行
        logging.info("Switching to root user and executing ru-controller...")
        commands = [
            "sudo su",  # rootに昇格
            "cd /run/media/mmcblk0p1/",  # 必要なディレクトリに移動
            "./ru-controller00.09.00.elf ru.txt &",  # ru-controllerを実行
        ]

        for command in commands:
            channel.send(command + "\n")
            time.sleep(1)
            if "sudo" in command and sudo_password:
                channel.send(sudo_password + "\n")
                time.sleep(1)

        logging.info("DUT setup completed.")
    except Exception as e:
        logging.error(f"Error during DUT setup: {e}")
    finally:
        client.close()

import time
import serial
import logging

def setup_dut_via_serial(port, baudrate):
    """シリアル接続でDUTを設定"""
    try:
        with serial.Serial(port, baudrate, timeout=10) as serial_conn:
            logging.info(f"Connected to DUT via Serial: {port} at {baudrate} bps")

            # ログインプロンプトの処理
            login_attempts = 0
            while True:
                # 少しずつデータを読み取る
                output = serial_conn.read(100).decode("utf-8")
                logging.debug(f"Serial output: {output.strip()}")  # シリアル出力をデバッグログとして表示

                if "login:" in output:
                    logging.debug(f"Received login prompt: {output.strip()}")
                    serial_conn.write(b"petalinux\n")  # ログインユーザー名
                elif "Password:" in output:
                    logging.debug(f"Received password prompt: {output.strip()}")
                    serial_conn.write(b"petalinux00\n")  # ログインパスワード
                elif "$" in output or "#" in output:  # ログイン成功を確認
                    logging.info("Login successful via Serial.")
                    break
                elif login_attempts >= 6:  # ログイン試行回数を制限
                    logging.error("Login failed after several attempts.")
                    return
                else:
                    # 再試行前に待機
                    logging.debug("No login prompt received, retrying...")
                    time.sleep(3)  # 少し待機して再試行
                    login_attempts += 1

            # `ru-controller`の確認
            logging.info("Checking if ru-controller is already running via Serial...")
            output = execute_serial_command(serial_conn, "ps aux | grep ru-controller")
            if "PLL Sync state 0xdd Locked" in output:
                logging.info("PLL Sync state 0xdd Locked detected, skipping ru-controller execution.")
                return

            # `sudo su`で昇格してru-controllerを実行
            logging.info("Switching to root user and executing ru-controller via Serial...")
            commands = [
                "sudo su",  # rootに昇格
                "cd /run/media/mmcblk0p1/",  # 必要なディレクトリに移動
                "./ru-controller00.09.00.elf ru.txt &",  # ru-controllerをバックグラウンドで実行
            ]
            for command in commands:
                execute_serial_command(serial_conn, command)
                time.sleep(2)

            logging.info("DUT setup via Serial completed.")
    except Exception as e:
        logging.error(f"Failed to setup DUT via Serial: {e}")
             
def setup_dut(connection_type, ip=None, user=None, password=None, sudo_password=None, port=None, baudrate=None):
    """DUTを設定する（SSHまたはSerial）"""
    if connection_type == "SSH":
        setup_dut_via_ssh(ip, user, password, sudo_password)
    elif connection_type == "Serial":
        setup_dut_via_serial(port, baudrate)
    else:
        logging.error("Invalid connection type. Choose 'SSH' or 'Serial'.")
