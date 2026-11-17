# -*- coding: utf-8 -*-
"""经跳板执行只读核查；凭据由环境变量或已授权文档读取，不输出凭据。

用法：python 只读远程核查.py <本地远程命令文件> [本地结果文件]
命令必须由复核者确认只读。本工具不会自动执行迁移或修改配置。
"""
import importlib.util
import os
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True  # 导入既有执行器时不在归档轮次生成缓存。
ROOT = Path(__file__).resolve().parents[2]


def load_credentials():
    text = (ROOT / "superset-部署与安装长任务计划-v1-多方互查修订版.md").read_text(encoding="utf-8")
    for marker, prefix in [("**跳板机(BI)**", "JB"), ("部署目标服务器", "TGT")]:
        if os.environ.get(prefix + "_PWD"):
            continue
        row = next(line for line in text.splitlines() if line.startswith("|") and marker in line)
        cell = row.split("|")[3].strip().replace("`", "")
        match = re.search(r"root\s*[/／]\s*(\S+)", cell)
        if not match:
            match = re.search(r"密码\s*[：:]?\s*([^\s；;，,]+)", cell)
        if not match:
            parts = cell.split()
            if len(parts) == 2 and parts[0] == "root":
                password = parts[1]
            else:
                raise RuntimeError("无法解析授权文档中的凭据，请设置 JB_PWD/TGT_PWD 环境变量")
        else:
            password = match.group(1)
        os.environ[prefix + "_USER"] = "root"
        os.environ[prefix + "_PWD"] = password


def main():
    load_credentials()
    spec = importlib.util.spec_from_file_location("approved_remote", ROOT / "review/round-3/远程执行.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gateway, target = module.connect()
    try:
        command = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
        _, stdout, stderr = target.exec_command(command, timeout=60)
        output = stdout.read().decode("utf-8", "replace")
        errors = stderr.read().decode("utf-8", "replace")
        rc = stdout.channel.recv_exit_status()
        # 错误可能包含连接信息，只返回退出码，不转储 stderr。
        if rc:
            print("REMOTE_FAILED", rc, "stderr_bytes", len(errors.encode("utf-8")))
            return rc
        if len(sys.argv) > 2:
            Path(sys.argv[2]).write_text(output, encoding="utf-8")
            print("SAVED", sys.argv[2], "bytes", len(output.encode("utf-8")))
        else:
            print(output)
        return 0
    finally:
        target.close()
        gateway.close()


if __name__ == "__main__":
    sys.exit(main())
