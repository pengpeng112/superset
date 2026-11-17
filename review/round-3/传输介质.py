# -*- coding: utf-8 -*-
"""经跳板机向 10.10.8.73 传输文件（SFTP over direct-tcpip 隧道）。

用法：
  JB_USER=root JB_PWD=... TGT_USER=root TGT_PWD=... python 传输介质.py <本地文件> <远程路径> [...]
凭据环境变量传入；大文件每 256MB 打印一次进度。
"""
import os
import stat
import sys
import time

import paramiko

JB_HOST, JB_PORT = "10.10.8.53", 40022
TGT_HOST, TGT_PORT = "10.10.8.73", 22
last_mb = -1


def main():
    pairs = sys.argv[1:]
    if not pairs or len(pairs) % 2 != 0:
        print("usage: 传输介质.py <local> <remote> [...]")
        return 2
    gw = paramiko.SSHClient()
    gw.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    gw.connect(JB_HOST, port=JB_PORT, username=os.environ["JB_USER"], password=os.environ["JB_PWD"], timeout=15)
    channel = gw.get_transport().open_channel("direct-tcpip", (TGT_HOST, TGT_PORT), ("127.0.0.1", 0))
    transport = paramiko.Transport(channel)
    transport.start_client(timeout=15)
    transport.auth_password(os.environ["TGT_USER"], os.environ["TGT_PWD"])
    sftp = paramiko.SFTPClient.from_transport(transport)

    for i in range(0, len(pairs), 2):
        global last_mb
        last_mb = -1
        local, remote = pairs[i], pairs[i + 1]
        size = os.path.getsize(local)
        t0 = time.time()

        def cb(done, total):
            global last_mb
            mb = int(done / 1048576)
            if mb >= last_mb + 256 or done == total:
                last_mb = mb
                rate = done / 1048576 / max(time.time() - t0, 0.001)
                print(f"[xfer] {os.path.basename(local)} {mb}MB/{int(total/1048576)}MB {rate:.1f}MB/s", flush=True)

        # 远端父目录不存在则创建
        rdir = remote.rsplit("/", 1)[0]
        try:
            sftp.stat(rdir)
        except FileNotFoundError:
            parts = rdir.strip("/").split("/")
            cur = ""
            for p in parts:
                cur += "/" + p
                try:
                    sftp.stat(cur)
                except FileNotFoundError:
                    sftp.mkdir(cur)
        sftp.put(local, remote, callback=cb)
        rl = sftp.stat(remote)
        ok = "OK" if rl.st_size == size else "SIZE-MISMATCH"
        print(f"[xfer] {local} -> {remote} {ok} ({size} bytes)", flush=True)
    sftp.close()
    transport.close()
    gw.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
