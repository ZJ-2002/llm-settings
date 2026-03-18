#!/usr/bin/env python3
"""
子代理心跳守护进程
由 Leader 在启动子代理时一并启动

功能：
1. 定期更新 active_teams.json 中的心跳时间戳
2. 监控父进程（Leader）存活状态
3. 如果 Leader 丢失，执行自杀协议

使用方法：
    python3 heartbeat_daemon.py <team_id> <leader_pid>

示例：
    python3 heartbeat_daemon.py team-001 12345
"""

import json
import os
import shutil
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# 配置
HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）
STATE_DIR = Path(".state")
TEAMS_FILE = STATE_DIR / "active_teams.json"


def log(msg: str):
    """输出带时间戳的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Heartbeat {timestamp}] {msg}", flush=True)


def load_json(path: Path) -> dict | None:
    """安全加载 JSON"""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None


def is_valid_json(path: Path) -> bool:
    """验证 JSON 有效性"""
    try:
        with open(path, 'r') as f:
            json.load(f)
        return True
    except:
        return False


def check_leader_alive(leader_pid: int) -> bool:
    """检查父进程是否存活"""
    try:
        # 发送信号 0 检查进程是否存在
        os.kill(leader_pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def atomic_update_heartbeat(team_id: str) -> bool:
    """
    原子更新心跳时间戳
    使用 .tmp -> .bak -> mv 协议
    """
    if not TEAMS_FILE.exists():
        return False
    
    tmp_path = TEAMS_FILE.with_suffix(".tmp")
    bak_path = TEAMS_FILE.with_suffix(".bak")
    
    try:
        # 读取当前数据
        data = load_json(TEAMS_FILE)
        if not data:
            return False
        
        # 修改匹配团队的时间戳
        updated = False
        for team in data.get("active_teams", []):
            if team["team_id"] == team_id:
                team["heartbeat"] = datetime.now().isoformat()
                updated = True
                break
        
        if not updated:
            return False  # 团队已被删除
        
        # 原子写入
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # 验证后替换
        if is_valid_json(tmp_path):
            shutil.copy(TEAMS_FILE, bak_path)
            shutil.move(str(tmp_path), str(TEAMS_FILE))
            return True
        else:
            log("错误: 生成的 JSON 无效")
            return False
            
    except Exception as e:
        log(f"更新心跳失败: {e}")
        return False
    finally:
        # 清理临时文件
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except:
                pass


def suicide_cleanup(team_id: str, leader_pid: int):
    """
    自杀前的清理
    尝试从注册表中移除自己
    """
    log(f"检测到 Leader (PID {leader_pid}) 已丢失，执行自杀协议...")
    
    # 可选：尝试清理注册表中的自己
    # 注意：这可能与 Leader 的收割逻辑竞争，所以不强制要求成功
    
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("用法: heartbeat_daemon.py <team_id> <leader_pid>")
        print("示例: heartbeat_daemon.py team-001 12345")
        sys.exit(1)
    
    team_id = sys.argv[1]
    leader_pid = int(sys.argv[2])
    
    log(f"心跳守护启动: team={team_id}, leader_pid={leader_pid}")
    
    # 设置信号处理
    def signal_handler(signum, frame):
        log(f"收到信号 {signum}，正常退出")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 确保状态目录存在
    if not STATE_DIR.exists():
        log(f"错误: 状态目录 {STATE_DIR} 不存在")
        sys.exit(1)
    
    # 主循环
    consecutive_failures = 0
    max_failures = 5  # 连续失败阈值
    
    while True:
        try:
            # 1. 自杀协议：检查父进程
            if not check_leader_alive(leader_pid):
                suicide_cleanup(team_id, leader_pid)
                break  # 不会执行到这里
            
            # 2. 更新心跳
            if atomic_update_heartbeat(team_id):
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    log(f"连续 {max_failures} 次更新失败，可能是团队已被解散")
                    # 不自杀，但降低更新频率
                    time.sleep(HEARTBEAT_INTERVAL * 2)
                    continue
            
            # 3. 等待下一个周期
            time.sleep(HEARTBEAT_INTERVAL)
            
        except KeyboardInterrupt:
            log("收到键盘中断，正常退出")
            break
        except Exception as e:
            log(f"心跳错误: {e}")
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                log(f"连续 {max_failures} 次异常，退出")
                break
            time.sleep(HEARTBEAT_INTERVAL)
    
    log("心跳守护正常退出")


if __name__ == "__main__":
    main()
