# Long-Running Recovery — 崩溃恢复协议

> 本文档定义了在各种异常中断场景下的恢复策略，确保长期运行的项目不会因意外中断而丢失进度。
> 
> **⭐ 重要更新**: 本 skill 已升级为 SQLite 数据库架构。恢复流程优先使用数据库事务，JSON 文件作为向后兼容和 Git 导出。

---

## 目录

- [启动验证序列](#启动验证序列流程图)
- [数据库恢复流程](#数据库恢复流程)
- [Git 版本一致性校验](#git-版本一致性校验)
- [各阶段详细恢复步骤](#各阶段详细恢复步骤)
- [中断场景及应对表](#中断场景及应对表)
- [错误恢复策略](#错误恢复策略)
- [预防措施](#预防措施减少恢复需求)
- [自动化恢复脚本](#自动化恢复脚本)
- [恢复后验证清单](#恢复后验证清单)

---

## 启动验证序列（流程图）

```
.state/ 目录存在？
│
├─ 否 → 全新项目，执行初始化协议
│         └─ 初始化完成后：
│             ├─ 初始化 SQLite 数据库
│             ├─ 记录当前 Git hash
│             └─ 退出当前会话
│
└─ 是 → 进入恢复流程
         │
         ├─ 数据库文件存在？
         │   ├─ 是 → 进入数据库恢复流程
         │   └─ 否 → 尝试从 JSON 文件迁移
         │
         ├─ Git hash 校验 ⭐
         │   ├─ 一致 → 继续
         │   └─ 不一致 → 警告用户选择同步策略
         │
         ├─ 清理中断的写入（.tmp 文件）
         │
         ├─ 事务一致性检查
         │   ├─ 无 in_progress 任务或已重置 → 继续
         │   └─ 发现孤儿任务 → 原子化重置为 pending
         │
         ├─ 任务依赖健康检查
         │   ├─ 无循环依赖 → 继续
         │   └─ 发现循环 → 标记 dependency_health 为 circular
         │
         ├─ 收割孤儿 Agent Teams
         │   └─ 终止残留进程，重置关联任务
         │
         └─ 导出 JSON 到 .state/（用于 Git）
```

---

## 数据库恢复流程

### SQLite 恢复优势

| 特性 | JSON 恢复 | SQLite 恢复 |
|------|----------|------------|
| 写入原子性 | 手动 `.tmp` → `.bak` → `mv` | 内置 ACID 事务 |
| 并发安全 | 文件锁，易冲突 | 行级锁 + WAL 模式 |
| 崩溃恢复 | 依赖 .bak 文件 | 自动回滚未提交事务 |
| 数据校验 | 手动 JSON 解析 | 内置完整性检查 |

### 数据库连接配置

```python
import sqlite3

def create_recovery_connection(db_path):
    """
    创建用于恢复的数据库连接
    - 启用 WAL 模式提高并发
    - 设置较长超时等待锁
    - 启用外键约束
    """
    conn = sqlite3.connect(db_path, timeout=60)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
```

### 恢复协议实现

```python
def recover_database(storage, current_git_hash=None, dry_run=False):
    """
    数据库恢复协议核心实现
    
    Args:
        storage: SkillStorage 实例
        current_git_hash: 当前 Git commit hash
        dry_run: 仅查看，不实际修改
    
    Returns:
        dict: 恢复结果报告
    """
    actions = []
    
    with storage._get_connection() as conn:
        # 1. Git hash 校验
        if current_git_hash:
            project = conn.execute(
                "SELECT git_hash FROM projects LIMIT 1"
            ).fetchone()
            
            if project and project['git_hash']:
                if project['git_hash'] != current_git_hash:
                    return {
                        "success": False,
                        "error": "git_hash_mismatch",
                        "recorded_hash": project['git_hash'][:7],
                        "current_hash": current_git_hash[:7],
                        "message": (
                            f"⚠️ 版本冲突：快照记录为 {project['git_hash'][:7]}，"
                            f"当前为 {current_git_hash[:7]}"
                        ),
                        "suggestions": [
                            "1. 执行 git checkout 回退到记录版本",
                            "2. 使用 force=True 以当前代码为准重置状态"
                        ]
                    }
                else:
                    actions.append(f"✓ Git hash 校验通过: {current_git_hash[:7]}")
        
        if dry_run:
            # 仅查询将要执行的操作
            orphans = conn.execute("""
                SELECT task_id, owner FROM tasks 
                WHERE status = 'in_progress'
            """).fetchall()
            return {
                "success": True,
                "dry_run": True,
                "would_reset_tasks": [dict(o) for o in orphans],
                "orphan_count": len(orphans)
            }
        
        # 2. 重置孤儿任务（原子操作）
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET status = 'pending', 
                owner = NULL,
                started_at = NULL,
                version = version + 1
            WHERE status = 'in_progress'
        """)
        reset_count = cursor.rowcount
        
        if reset_count > 0:
            actions.append(f"重置 {reset_count} 个孤儿任务 (in_progress → pending)")
        
        # 3. 检测循环依赖
        cycles = storage.detect_circular_dependencies()
        if cycles:
            actions.append(f"⚠️ 检测到 {len(cycles)} 个循环依赖")
            # 更新项目健康状态
            conn.execute("""
                UPDATE projects 
                SET status = 'failed', updated_at = ?
                WHERE project_id = (SELECT project_id FROM projects LIMIT 1)
            """, (datetime.now().isoformat(),))
        
        conn.commit()
    
    # 4. 收割孤儿 Teams（进程级）
    reaped_teams = reap_orphaned_teams(storage)
    if reaped_teams:
        actions.extend(reaped_teams)
    
    return {
        "success": True,
        "actions": actions,
        "orphan_tasks_reset": reset_count,
        "circular_dependencies": cycles,
        "orphan_teams_reaped": len(reaped_teams)
    }
```

---

## Git 版本一致性校验

### 问题场景

**代码-状态不同步**：用户通过 `git checkout` 回退了代码，但 `.state/` 目录保留了新的状态。

```
时间线:
T1: 完成任务 A, B (数据库记录 git_hash=abc123)
T2: git commit -m "完成任务 A, B"
T3: git checkout HEAD~1  (回退到只有任务 A 完成的状态)
T4: 启动新会话
    └─ 数据库状态: B=completed
    └─ 代码状态: B 未实现 (因为回退了)
    └─ ⚠️ 逻辑撕裂！
```

### 校验实现

```python
def verify_git_consistency(storage, current_hash, auto_fix=False):
    """
    校验并修复 Git 版本一致性
    
    Args:
        auto_fix: 是否自动以代码为准重置状态
    """
    project = storage.get_project(project_id="default")
    recorded_hash = project.get('git_hash') if project else None
    
    if not recorded_hash:
        # 旧项目没有记录，更新为当前
        storage.update_project_git_hash("default", current_hash)
        return {"status": "updated", "message": "已记录当前 Git hash"}
    
    if recorded_hash == current_hash:
        return {"status": "consistent", "message": "版本一致"}
    
    # 版本不一致
    result = {
        "status": "mismatch",
        "recorded_hash": recorded_hash[:7],
        "current_hash": current_hash[:7],
        "options": []
    }
    
    # 检查哪个版本更新
    try:
        is_ancestor = subprocess.run(
            ['git', 'merge-base', '--is-ancestor', recorded_hash, current_hash],
            capture_output=True
        ).returncode == 0
        
        if is_ancestor:
            result["situation"] = "代码超前于状态（正常前进）"
            result["suggestion"] = "更新数据库中的 git_hash 记录"
            if auto_fix:
                storage.update_project_git_hash("default", current_hash)
                result["action"] = "已更新 git_hash 记录"
        else:
            result["situation"] = "代码回退（状态超前）"
            result["suggestion"] = "需要决定同步策略"
            result["options"] = [
                "1. git checkout {recorded_hash}  # 回退代码到状态版本",
                "2. recover(force=True)  # 以当前代码为准重置所有任务",
                "3. 手动调整任务状态后重新提交"
            ]
    except:
        result["situation"] = "无法判断版本关系"
    
    return result
```

### 恢复时交互示例

```
$ recover()

⚠️ 版本冲突检测
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
记录版本: abc1234 (3天前)
当前版本: def5678 (刚刚)
状态: 代码回退，状态超前

可能原因:
- 使用 git checkout 回退了代码
- 从其他分支切换过来

请选择同步策略:
[1] 回退代码到记录版本 (git checkout abc1234)
[2] 以当前代码为准，重置所有任务状态
[3] 查看详细差异后决定

> 2

执行操作:
✓ 重置 5 个 in_progress 任务
✓ 重置 3 个 completed 任务（在当前代码中不存在）
✓ 更新 git_hash 记录为 def5678

恢复完成。建议: 重新规划当前代码版本的任务。
```

---

## 各阶段详细恢复步骤

### 阶段 1：Git Hash 校验 ⭐ 新增

```python
def phase_1_git_verification(storage, force=False):
    """
    阶段 1: Git 版本一致性校验
    """
    current_hash = get_current_git_hash()
    if not current_hash:
        return {"skipped": True, "reason": "不是 Git 仓库"}
    
    result = verify_git_consistency(storage, current_hash, auto_fix=False)
    
    if result["status"] == "mismatch" and not force:
        return {
            "success": False,
            "phase": "git_verification",
            "error": "版本冲突",
            "details": result,
            "hint": "使用 force=True 强制以当前代码为准，或先执行 git checkout"
        }
    
    return {"success": True, "git_hash": current_hash}
```

### 阶段 2：清理中断写入

```python
def phase_2_cleanup_tmp_files(state_dir):
    """
    阶段 2: 清理 .tmp 临时文件
    （向后兼容 JSON 文件）
    """
    actions = []
    tmp_files = list(Path(state_dir).glob("*.tmp"))
    
    for tmp_file in tmp_files:
        tmp_file.unlink()
        actions.append(f"已删除: {tmp_file.name}")
    
    return {"success": True, "actions": actions}
```

### 阶段 3：数据库级孤儿任务恢复 ⭐

```python
def phase_3_recover_orphan_tasks(storage, dry_run=False):
    """
    阶段 3: 原子化重置孤儿任务
    
    使用数据库事务确保原子性：
    - 要么全部重置成功
    - 要么全部保持原状
    """
    with storage._get_connection() as conn:
        # 先查询有哪些孤儿任务
        orphans = conn.execute("""
            SELECT task_id, owner, started_at 
            FROM tasks 
            WHERE status = 'in_progress'
        """).fetchall()
        
        if not orphans:
            return {"success": True, "actions": ["无孤儿任务"]}
        
        actions = [f"发现 {len(orphans)} 个孤儿任务"]
        
        if dry_run:
            for o in orphans:
                actions.append(f"  └─ 将重置: {o['task_id']} (执行者: {o['owner']})")
            return {"success": True, "dry_run": True, "actions": actions}
        
        # 原子化重置
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET status = 'pending',
                owner = NULL,
                started_at = NULL,
                version = version + 1
            WHERE status = 'in_progress'
        """)
        
        conn.commit()
        
        for o in orphans:
            actions.append(f"  └─ 已重置: {o['task_id']}")
        
        return {
            "success": True,
            "actions": actions,
            "reset_count": cursor.rowcount
        }
```

### 阶段 4：任务依赖健康检查

```python
def phase_4_dependency_health_check(storage):
    """
    阶段 4: DAG 健康检查
    """
    cycles = storage.detect_circular_dependencies()
    
    actions = []
    if cycles:
        actions.append(f"⚠️ 检测到 {len(cycles)} 个循环依赖:")
        for cycle in cycles:
            actions.append(f"    {' -> '.join(cycle)}")
    else:
        actions.append("✓ 无循环依赖")
    
    # 检测缺失依赖
    with storage._get_connection() as conn:
        missing = conn.execute("""
            SELECT td.task_id, td.depends_on_id 
            FROM task_dependencies td
            LEFT JOIN tasks t ON td.depends_on_id = t.task_id
            WHERE t.task_id IS NULL
        """).fetchall()
        
        if missing:
            actions.append(f"⚠️ 检测到 {len(missing)} 个缺失依赖:")
            for m in missing:
                actions.append(f"    任务 {m['task_id']} 依赖不存在的 {m['depends_on_id']}")
    
    return {
        "success": True,
        "actions": actions,
        "circular": cycles,
        "missing": missing
    }
```

### 阶段 5：收割孤儿 Agent Teams

```python
def phase_5_reap_orphan_teams(storage):
    """
    阶段 5: 收割孤儿 Teams
    """
    import psutil
    
    with storage._get_connection() as conn:
        teams = conn.execute("""
            SELECT t.team_id, tm.pid, tm.member_id
            FROM teams t
            JOIN team_members tm ON t.team_id = tm.team_id
            WHERE t.status = 'active'
        """).fetchall()
        
        actions = []
        reaped_count = 0
        
        for team in teams:
            pid = team['pid']
            if pid and not psutil.pid_exists(pid):
                # 进程已终止，标记为孤儿
                conn.execute("""
                    UPDATE teams SET status = 'failed', updated_at = ?
                    WHERE team_id = ?
                """, (datetime.now().isoformat(), team['team_id']))
                
                actions.append(f"标记孤儿团队: {team['team_id']} (PID {pid} 已终止)")
                reaped_count += 1
        
        conn.commit()
        
        return {
            "success": True,
            "actions": actions,
            "reaped_count": reaped_count
        }
```

### 阶段 6：导出 JSON（Git 同步）

```python
def phase_6_export_to_json(storage, state_dir):
    """
    阶段 6: 导出数据库状态到 JSON（用于 Git 提交）
    """
    checkpoint = storage.get_stats()
    
    # 导出 checkpoint.json
    checkpoint_path = Path(state_dir) / "checkpoint.json"
    with open(checkpoint_path, 'w') as f:
        json.dump(checkpoint, f, indent=2, default=str)
    
    # 导出 task-queue.json
    tasks = storage.get_tasks_by_status(None)
    task_queue_path = Path(state_dir) / "task-queue.json"
    with open(task_queue_path, 'w') as f:
        json.dump({"version": 1, "tasks": tasks}, f, indent=2, default=str)
    
    return {
        "success": True,
        "actions": [
            f"导出 checkpoint.json",
            f"导出 task-queue.json ({len(tasks)} 个任务)"
        ]
    }
```

---

## 中断场景及应对表

| # | 场景 | 症状 | 恢复方式 |
|---|------|------|---------|
| 1 | Agent 执行中崩溃 | 任务状态 `in_progress` | `recover()` 原子化重置为 `pending` |
| 2 | Git checkout 回退代码 | Git hash 不匹配 | `recover()` 警告，选择同步策略 |
| 3 | 多 Agent 竞争任务 | `atomic_start_task()` 返回 False | 自动选择其他任务 |
| 4 | 数据库锁定超时 | `database is locked` | 增加连接超时，重试 |
| 5 | 磁盘满导致写入失败 | SQLite 错误 | 清理空间后重新执行 |
| 6 | Agent Teams Leader 崩溃 | Teams 表中有残留记录 | `recover()` 标记孤儿团队 |
| 7 | 循环依赖导致死锁 | `detect_circular_dependencies()` 发现环路 | 提示用户修复依赖关系 |
| 8 | 代码-状态严重不同步 | Git hash 不匹配且非祖先关系 | 强制选择同步策略 |

---

## 错误恢复策略

### 自适应重试机制

```python
def record_error_with_retry(error_content, context=""):
    """
    记录错误并获取重试建议
    
    根据错误类型提供不同的重试策略：
    - 工具格式错误：最多 2 次重试
    - Bash 执行错误：最多 4 次重试
    - 业务逻辑错误：最多 5 次重试
    """
    error_patterns = {
        'tool_format': ['format', 'validation', 'schema', 'parse'],
        'bash': ['exit code', 'command not found', 'permission denied'],
        'business': ['timeout', 'rate limit', 'temporary']
    }
    
    error_lower = error_content.lower()
    
    for error_type, patterns in error_patterns.items():
        if any(p in error_lower for p in patterns):
            max_retries = {'tool_format': 2, 'bash': 4, 'business': 5}[error_type]
            return {
                "error_type": error_type,
                "max_retries": max_retries,
                "suggestion": f"建议重试（最多 {max_retries} 次）"
            }
    
    return {"error_type": "unknown", "max_retries": 3}
```

### 重复错误检测

```python
def detect_repeating_errors(storage, team_name, window=5):
    """
    检测是否在重复犯同样的错误（自我修正循环）
    """
    with storage._get_connection() as conn:
        recent_errors = conn.execute("""
            SELECT error_content, COUNT(*) as count
            FROM error_logs
            WHERE team_name = ? AND created_at > datetime('now', '-1 hour')
            GROUP BY error_content
            HAVING count >= ?
        """, (team_name, window)).fetchall()
        
        if recent_errors:
            return {
                "is_looping": True,
                "errors": [dict(e) for e in recent_errors],
                "suggestion": "检测到重复错误模式，建议：1) 查阅知识库 2) 寻求人工介入"
            }
        
        return {"is_looping": False}
```

---

## 预防措施（减少恢复需求）

1. **强制 recover**: 每个会话开始自动执行，校验 Git hash
2. **原子申领**: 使用 `atomic_start_task()` 而非直接修改
3. **频繁提交**: 每完成小步骤就 `git commit`
4. **先更新状态**: 任务开始时先标记 `in_progress`
5. **小任务粒度**: 每个任务能在单次会话完成
6. **状态与代码同步提交**: `.state/` 和代码在同一个 commit
7. **使用事务**: 多个相关操作使用数据库事务包裹
8. **心跳机制**: Agent Teams 使用 Pipe 监控替代文件心跳

---

## 自动化恢复脚本

### 完整 recover() 实现

```python
def recover(project_dir=".", force=False, dry_run=False):
    """
    执行完整的恢复协议
    """
    state_dir = Path(project_dir) / ".state"
    db_path = state_dir / "project_storage.db"
    
    # 初始化 storage
    storage = SkillStorage(str(db_path))
    
    results = {
        "success": True,
        "phases": [],
        "actions": []
    }
    
    # 阶段 1: Git 校验
    current_hash = get_current_git_hash()
    git_result = phase_1_git_verification(storage, force)
    results["phases"].append(git_result)
    
    if not git_result.get("success") and not force:
        return git_result
    
    # 阶段 2: 清理 tmp 文件
    cleanup_result = phase_2_cleanup_tmp_files(state_dir)
    results["phases"].append(cleanup_result)
    results["actions"].extend(cleanup_result.get("actions", []))
    
    # 阶段 3: 恢复孤儿任务
    orphan_result = phase_3_recover_orphan_tasks(storage, dry_run)
    results["phases"].append(orphan_result)
    results["actions"].extend(orphan_result.get("actions", []))
    
    # 阶段 4: 依赖健康检查
    health_result = phase_4_dependency_health_check(storage)
    results["phases"].append(health_result)
    results["actions"].extend(health_result.get("actions", []))
    
    # 阶段 5: 收割孤儿 Teams
    if not dry_run:
        teams_result = phase_5_reap_orphan_teams(storage)
        results["phases"].append(teams_result)
        results["actions"].extend(teams_result.get("actions", []))
    
    # 阶段 6: 导出 JSON
    if not dry_run:
        export_result = phase_6_export_to_json(storage, state_dir)
        results["phases"].append(export_result)
        results["actions"].extend(export_result.get("actions", []))
    
    return results
```

---

## 恢复后验证清单

- [ ] Git hash 校验通过（或已明确处理版本冲突）
- [ ] 数据库可连接且表结构正确
- [ ] 无 `in_progress` 任务残留（或已记录重置）
- [ ] 无循环依赖警告（`dependency_health` 为 valid）
- [ ] 孤儿 Teams 已收割
- [ ] checkpoint.json 和 task-queue.json 已导出（可选）
- [ ] session-log.md 格式正确

---

**相关文档**:
- `infrastructure.md` - 数据库架构详解
- `agent-teams.md` - Agent Teams 协作与心跳
- `sop.md` - 标准操作规程
