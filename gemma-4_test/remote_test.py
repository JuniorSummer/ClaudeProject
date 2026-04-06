"""
远程服务器测试脚本
通过SSH连接远程服务器执行显存测试
"""

import paramiko
import sys
import time

class RemoteTester:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.ssh = None

    def connect(self):
        """连接远程服务器"""
        print(f"连接服务器 {self.host}:{self.port}...")
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            timeout=30
        )
        print("连接成功!")

    def disconnect(self):
        """断开连接"""
        if self.ssh:
            self.ssh.close()
            print("已断开连接")

    def run_command(self, command, timeout=600):
        """执行远程命令"""
        print(f"\n执行命令: {command[:50]}...")

        channel = self.ssh.get_transport().open_session()
        channel.exec_command(command)

        output = []
        start = time.time()

        while True:
            if channel.exit_status_ready():
                while channel.recv_ready():
                    output.append(channel.recv(4096).decode())
                while channel.recv_stderr_ready():
                    output.append(channel.recv_stderr(4096).decode())
                break

            if channel.recv_ready():
                data = channel.recv(4096).decode()
                output.append(data)
                print(data, end='')
                sys.stdout.flush()

            if channel.recv_stderr_ready():
                data = channel.recv_stderr(4096).decode()
                output.append(data)
                print(data, end='')
                sys.stdout.flush()

            time.sleep(0.2)

            if time.time() - start > timeout:
                print("\n命令超时!")
                break

        return ''.join(output)

    def check_gpu(self):
        """检查GPU信息"""
        print("\n检查GPU信息...")
        result = self.run_command('nvidia-smi --query-gpu=name,memory.total --format=csv')
        return result

    def upload_script(self, local_path, remote_path):
        """上传脚本到服务器"""
        print(f"上传脚本: {local_path} -> {remote_path}")
        sftp = self.ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print("上传完成!")

    def test_gemma_31b(self, model_path):
        """测试Gemma-4-31B"""
        print("\n" + "=" * 60)
        print("测试 Gemma-4-31B")
        print("=" * 60)

        # 上传测试脚本
        self.upload_script('test_gemma_31b.py', '/root/test_gemma_31b.py')

        # 执行测试
        result = self.run_command('/root/miniconda3/bin/python /root/test_gemma_31b.py')
        return result


def main():
    # 配置服务器信息
    host = "connect.westb.seetacloud.com"
    port = 26295
    username = "root"
    password = "YOUR_PASSWORD"  # 请替换为实际密码

    tester = RemoteTester(host, port, username, password)

    try:
        tester.connect()

        # 检查GPU
        tester.check_gpu()

        # 测试Gemma-4-31B
        tester.test_gemma_31b("/root/autodl-tmp/models/google/gemma-4-31B-it")

    except Exception as e:
        print(f"错误: {e}")
    finally:
        tester.disconnect()


if __name__ == "__main__":
    main()
