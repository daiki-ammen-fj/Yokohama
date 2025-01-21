#!python3.11
# step2_DUT_setup.py

import paramiko
import time
import logging

def create_ssh_client(ip, user, password):
    """SSHクライアントを作成して接続する"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 未知のホストキーを自動的に追加
        client.connect(ip, username=user, password=password)
        logging.info(f"Connected to {ip}")
        return client
    except Exception as e:
        logging.error(f"Failed to connect to {ip}: {e}")
        return None

def execute_command(client, command):
    """指定したコマンドをSSH経由で実行"""
    try:
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()
        if output:
            logging.info(output)
        if error:
            logging.error(error)
        return output, error
    except Exception as e:
        logging.error(f"Failed to execute command {command}: {e}")
        return None, str(e)

def setup_dut(ip, user, password, sudo_password):
    """DUTを設定する"""
    # DUTにSSH接続
    client = create_ssh_client(ip, user, password)
    if not client:
        logging.error(f"Failed to connect to DUT {ip}.")
        return

    # まずはru-controllerの実行結果にPLL Syncの状態が含まれているか確認
    output, error = execute_command(client, "ps aux | grep ru-controller")
    if output and "PLL Sync state 0xdd Locked" in output:
        logging.info("PLL Sync state 0xdd Locked detected, skipping ru-controller execution.")
        client.close()
        return

    # ru-controllerがまだ実行されていなければ実行
    logging.info("Executing ru-controller...")
    commands = [
        "sudo su",  # rootに昇格
        "cd /run/media/mmcblk0p1/",  # 必要なディレクトリに移動
        "./ru-controller00.09.00.elf ru.txt &",  # ru-controllerを実行
    ]

    # 各コマンドを実行
    for command in commands:
        output, error = execute_command(client, command)
        if "Password" in error:
            stdin, stdout, stderr = client.exec_command(sudo_password + '\n')
            output = stdout.read().decode()
            logging.info(output)

            # sudo認証後の少しの遅延を追加してから次のコマンドを実行
            time.sleep(1)

        time.sleep(2)  # コマンド間の待機時間を調整

    logging.info("DUT setup completed.")
    client.close()
