"""
SkillStorage - Long-Running Skill 数据库包装器

提供原子化任务操作、Git 版本校验、崩溃恢复等功能。
基于 SQLite 实现 ACID 事务和乐观锁（CAS）。

Usage:
    from skill_storage import SkillStorage
    
    storage = SkillStorage(".state/project_storage.db")
    success, msg = storage.atomic_start_task("task-001")
    if success:
        # 执行任务...
        storage.complete_task("task-001")
"""

import sqlite3
import os
import subprocess
import json
from datetime import datetime
from contextlib import contextmanager
from typing import List, Dict, Tuple, Optional, Any


class SkillStorage:
    """
    长期运行项目的状态存储包装器。
    
    特性：
    - 乐观锁（CAS）防止并发冲突
    - Git hash 绑定确保代码版本一致
    - 原子化任务状态流转
    - 自动数据库初始化和迁移
    """
    
    def __init__(self, db_path: str = ".state/project_storage.db"):
        """
        初始化 SkillStorage 实例。
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_dir()
        self.init_db()
    
    def _ensure_dir(self):
        """确保数据库目录存在。"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """
        获取数据库连接的上下文管理器。
        
        Yields:
            sqlite3.Connection: 配置好的数据库连接
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        """
        初始化数据库表结构。
        如果表已存在则跳过。
        """
        with self._get_connection() as conn:
            conn.executescript("""
                -- 项目核心状态表
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'failed')),
                    git_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 任务队列表
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked')),
                    priority TEXT DEFAULT 'medium',
                    retry_count INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 0,
                    owner TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                -- 任务依赖表（DAG 支持）
                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT,
                    depends_on_id TEXT,
                    PRIMARY KEY (task_id, depends_on_id),
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                    FOREIGN KEY(depends_on_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                );

                -- 知识库与决策记录
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    topic TEXT,
                    decision TEXT NOT NULL,
                    rationale TEXT,
                    context_tags TEXT,  -- JSON 数组
                    task_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
                );

                -- Agent Teams 注册表
                CREATE TABLE IF NOT EXISTS teams (
                    team_id TEXT PRIMARY KEY,
                    project_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'failed')),
                    agent_type TEXT DEFAULT 'team-lead',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                -- 团队成员表
                CREATE TABLE IF NOT EXISTS team_members (
                    member_id TEXT PRIMARY KEY,
                    team_id TEXT,
                    name TEXT NOT NULL,
                    role TEXT,
                    pid INTEGER,
                    last_heartbeat TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
                );

                -- 成果文件表
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    team_id TEXT,
                    creator TEXT,
                    creator_role TEXT,
                    artifact_type TEXT CHECK(artifact_type IN ('research_note', 'review_report', 'analysis_result', 'design_doc', 'code_snippet', 'log_file', 'temp_data', 'other')),
                    title TEXT NOT NULL,
                    content TEXT,
                    summary TEXT,
                    visibility TEXT DEFAULT 'team' CHECK(visibility IN ('public', 'team', 'leader_only', 'private')),
                    tags TEXT,  -- JSON 数组
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(team_id) REFERENCES teams(team_id) ON DELETE CASCADE
                );

                -- 会话日志表
                CREATE TABLE IF NOT EXISTS session_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT,
                    session_id TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(project_id) ON DELETE CASCADE
                );

                -- 创建索引以优化查询
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner);
                CREATE INDEX IF NOT EXISTS idx_deps_task ON task_dependencies(task_id);
                CREATE INDEX IF NOT EXISTS idx_deps_depends ON task_dependencies(depends_on_id);
                CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_base(project_id);
                CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_base(topic);
                CREATE INDEX IF NOT EXISTS idx_teams_project ON teams(project_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_team ON artifacts(team_id);
            """)
            conn.commit()
    
    # ==================== 项目操作 ====================
    
    def create_project(self, project_id: str, name: str, git_hash: Optional[str] = None) -> bool:
        """
        创建新项目。
        
        Args:
            project_id: 项目唯一标识
            name: 项目名称
            git_hash: 当前 Git commit hash
            
        Returns:
            bool: 是否创建成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO projects (project_id, name, git_hash)
                    VALUES (?, ?, ?)
                """, (project_id, name, git_hash))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """获取项目信息。"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id = ?",
                (project_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def update_project_git_hash(self, project_id: str, git_hash: str):
        """更新项目的 Git hash。"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE projects 
                SET git_hash = ?, updated_at = ?
                WHERE project_id = ?
            """, (git_hash, datetime.now().isoformat(), project_id))
            conn.commit()
    
    # ==================== 原子化任务操作 ====================
    
    def atomic_start_task(self, task_id: str, owner: Optional[str] = None) -> Tuple[bool, str]:
        """
        原子化启动任务。
        
        使用 version 字段实现 CAS (Compare-And-Swap)，
        防止多个 Agent 同时抢占同一任务。
        
        Args:
            task_id: 任务 ID
            owner: 任务执行者标识
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'in_progress', 
                    started_at = ?, 
                    owner = ?,
                    version = version + 1
                WHERE task_id = ? AND status = 'pending'
            """, (datetime.now().isoformat(), owner, task_id))
            
            if cursor.rowcount == 0:
                # 检查任务状态
                row = conn.execute(
                    "SELECT status, owner FROM tasks WHERE task_id = ?",
                    (task_id,)
                ).fetchone()
                if row:
                    return False, f"任务已被抢占 - 当前状态: {row['status']}, 执行者: {row['owner']}"
                return False, "任务不存在"
            
            conn.commit()
            return True, "任务启动成功"
    
    def complete_task(self, task_id: str) -> Tuple[bool, str]:
        """
        原子化完成任务。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'completed', 
                    completed_at = ?,
                    version = version + 1
                WHERE task_id = ? AND status = 'in_progress'
            """, (datetime.now().isoformat(), task_id))
            
            if cursor.rowcount == 0:
                return False, "任务不存在或不在执行中"
            
            conn.commit()
            return True, "任务完成"
    
    def fail_task(self, task_id: str, increment_retry: bool = True) -> Tuple[bool, str]:
        """
        标记任务失败。
        
        Args:
            task_id: 任务 ID
            increment_retry: 是否增加重试计数
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            if increment_retry:
                conn.execute("""
                    UPDATE tasks 
                    SET status = 'failed', 
                        retry_count = retry_count + 1,
                        version = version + 1
                    WHERE task_id = ?
                """, (task_id,))
            else:
                conn.execute("""
                    UPDATE tasks 
                    SET status = 'failed',
                        version = version + 1
                    WHERE task_id = ?
                """, (task_id,))
            conn.commit()
            return True, "任务已标记为失败"
    
    def reset_task(self, task_id: str) -> Tuple[bool, str]:
        """
        重置任务到 pending 状态。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tasks 
                SET status = 'pending', 
                    owner = NULL,
                    started_at = NULL,
                    version = version + 1
                WHERE task_id = ?
            """, (task_id,))
            conn.commit()
            return True, "任务已重置"
    
    def block_task(self, task_id: str) -> Tuple[bool, str]:
        """
        阻塞任务。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'blocked',
                    version = version + 1
                WHERE task_id = ? AND status IN ('pending', 'failed')
            """, (task_id,))
            
            if cursor.rowcount == 0:
                return False, "任务不存在或无法阻塞（只能阻塞 pending 或 failed 状态的任务）"
            
            conn.commit()
            return True, "任务已阻塞"
    
    def unblock_task(self, task_id: str) -> Tuple[bool, str]:
        """
        解除任务阻塞，重置为 pending 状态。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'pending',
                    version = version + 1
                WHERE task_id = ? AND status = 'blocked'
            """, (task_id,))
            
            if cursor.rowcount == 0:
                return False, "任务不存在或未处于阻塞状态"
            
            conn.commit()
            return True, "任务已解除阻塞"
    
    # ==================== 任务 CRUD ====================
    
    def create_task(
        self,
        task_id: str,
        project_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        status: str = "pending"
    ) -> Tuple[bool, str]:
        """
        创建新任务。
        
        Args:
            task_id: 任务唯一标识
            project_id: 所属项目 ID
            title: 任务标题
            description: 任务描述
            priority: 优先级 (high/medium/low)
            status: 初始状态 (pending/in_progress/completed/failed/blocked)
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tasks (task_id, project_id, title, description, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, project_id, title, description, priority, status))
                conn.commit()
            return True, f"任务 {task_id} 创建成功"
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint" in str(e):
                return False, f"任务 ID '{task_id}' 已存在"
            return False, f"创建任务失败: {str(e)}"
    
    def bulk_create_tasks(
        self,
        project_id: str,
        tasks: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """
        批量创建任务。
        
        Args:
            project_id: 所属项目 ID
            tasks: 任务列表，每个任务为 dict，包含 task_id, title, description, priority 等
            
        Returns:
            Tuple[int, List[str]]: (成功创建数量, 错误列表)
        """
        success_count = 0
        errors = []
        
        with self._get_connection() as conn:
            for task in tasks:
                try:
                    conn.execute("""
                        INSERT INTO tasks (task_id, project_id, title, description, priority, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        task['task_id'],
                        project_id,
                        task.get('title', ''),
                        task.get('description', ''),
                        task.get('priority', 'medium'),
                        task.get('status', 'pending')
                    ))
                    success_count += 1
                except sqlite3.IntegrityError as e:
                    errors.append(f"任务 {task.get('task_id', '?')}: {str(e)}")
            
            conn.commit()
        
        return success_count, errors
    
    def update_task(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        更新任务信息（不改变状态）。
        
        Args:
            task_id: 任务 ID
            title: 新标题（可选）
            description: 新描述（可选）
            priority: 新优先级（可选）
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        
        if not updates:
            return True, "没有需要更新的字段"
        
        params.append(task_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE tasks 
                SET {', '.join(updates)}
                WHERE task_id = ?
            """, params)
            
            if cursor.rowcount == 0:
                return False, "任务不存在"
            
            conn.commit()
            return True, "任务更新成功"
    
    def delete_task(self, task_id: str) -> Tuple[bool, str]:
        """
        删除任务及其依赖关系。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            # 检查任务是否存在
            row = conn.execute(
                "SELECT 1 FROM tasks WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            
            if not row:
                return False, "任务不存在"
            
            # 删除任务（依赖关系会自动级联删除）
            conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return True, f"任务 {task_id} 已删除"
    
    def get_all_tasks(
        self,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取所有任务列表。
        
        Args:
            project_id: 可选的项目过滤
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 任务列表
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM tasks"
            params = []
            
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            
            query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    def get_task_with_dependencies(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详情及其依赖关系。
        
        Args:
            task_id: 任务 ID
            
        Returns:
            Dict: 包含任务信息和依赖列表的字典，任务不存在返回 None
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        # 获取依赖的任务
        dependencies = self.get_task_dependencies(task_id)
        
        # 获取被哪些任务依赖
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT t.* FROM tasks t
                JOIN task_dependencies td ON t.task_id = td.task_id
                WHERE td.depends_on_id = ?
            """, (task_id,)).fetchall()
            dependents = [dict(row) for row in rows]
        
        task['dependencies'] = dependencies
        task['dependents'] = dependents
        
        return task
    
    # ==================== 任务查询 ====================
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情。"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?",
                (task_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def get_ready_tasks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取可执行的任务列表（依赖已满足）。
        
        查询所有 pending 状态且没有未完成依赖的任务。
        
        Args:
            project_id: 可选的项目过滤
            
        Returns:
            List[Dict]: 可执行任务列表
        """
        with self._get_connection() as conn:
            query = """
                SELECT t.* FROM tasks t
                WHERE t.status = 'pending'
                AND NOT EXISTS (
                    SELECT 1 FROM task_dependencies td
                    JOIN tasks dep ON td.depends_on_id = dep.task_id
                    WHERE td.task_id = t.task_id
                    AND dep.status != 'completed'
                )
            """
            params = []
            if project_id:
                query += " AND t.project_id = ?"
                params.append(project_id)
            
            query += " ORDER BY CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
            
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    def get_tasks_by_status(self, status: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """按状态获取任务列表。"""
        with self._get_connection() as conn:
            query = "SELECT * FROM tasks WHERE status = ?"
            params = [status]
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    # ==================== 任务依赖管理 ====================
    
    def add_task_dependency(self, task_id: str, depends_on_id: str) -> Tuple[bool, str]:
        """
        添加任务依赖关系。
        
        Args:
            task_id: 依赖方任务 ID
            depends_on_id: 被依赖方任务 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO task_dependencies (task_id, depends_on_id)
                    VALUES (?, ?)
                """, (task_id, depends_on_id))
                conn.commit()
            return True, "依赖添加成功"
        except sqlite3.IntegrityError as e:
            return False, f"依赖添加失败: {str(e)}"
    
    def get_task_dependencies(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的依赖列表。"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT t.* FROM tasks t
                JOIN task_dependencies td ON t.task_id = td.depends_on_id
                WHERE td.task_id = ?
            """, (task_id,)).fetchall()
            return [dict(row) for row in rows]
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        检测循环依赖。
        
        Returns:
            List[List[str]]: 检测到的环路列表
        """
        with self._get_connection() as conn:
            # 获取所有依赖关系
            rows = conn.execute(
                "SELECT task_id, depends_on_id FROM task_dependencies"
            ).fetchall()
            
            # 构建图
            graph = {}
            for row in rows:
                if row['task_id'] not in graph:
                    graph[row['task_id']] = []
                graph[row['task_id']].append(row['depends_on_id'])
            
            # DFS 检测环路
            cycles = []
            visited = set()
            rec_stack = set()
            path = []
            seen_cycles = set()  # 用于环路去重
            
            def dfs(node):
                visited.add(node)
                rec_stack.add(node)
                path.append(node)

                if node in graph:
                    for neighbor in graph[node]:
                        if neighbor not in visited:
                            dfs(neighbor)
                        elif neighbor in rec_stack:
                            # 发现环路 - 提取从 neighbor 开始的完整循环路径
                            cycle_start = path.index(neighbor)
                            cycle_path = path[cycle_start:] + [neighbor]
                            # 标准化环路表示（从最小元素开始）用于去重
                            normalized = tuple(min_rotation(cycle_path[:-1]) + [cycle_path[0]])
                            if normalized not in seen_cycles:
                                seen_cycles.add(normalized)
                                cycles.append(cycle_path)

                path.pop()
                rec_stack.remove(node)

            def min_rotation(arr):
                """返回数组的最小旋转形式，用于环路标准化"""
                if not arr:
                    return arr
                n = len(arr)
                if n == 1:
                    return arr
                # 找到最小元素的索引
                min_idx = 0
                for i in range(1, n):
                    if arr[i] < arr[min_idx]:
                        min_idx = i
                # 从最小元素开始旋转
                return arr[min_idx:] + arr[:min_idx]

            for node in graph:
                if node not in visited:
                    dfs(node)

            return cycles
    
    # ==================== 崩溃恢复 ====================
    
    def recover_orphaned_tasks(
        self, 
        current_git_hash: Optional[str] = None,
        reset_in_progress: bool = True
    ) -> Tuple[bool, str]:
        """
        崩溃恢复协议的核心实现。
        
        1. 校验 Git Hash 确保代码版本一致
        2. 将所有卡在 'in_progress' 的任务重置为 'pending'
        
        Args:
            current_git_hash: 当前 Git commit hash
            reset_in_progress: 是否重置进行中的任务
            
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        with self._get_connection() as conn:
            # 1. Git hash 校验
            if current_git_hash:
                project = conn.execute(
                    "SELECT git_hash FROM projects LIMIT 1"
                ).fetchone()
                
                if project and project['git_hash']:
                    if project['git_hash'] != current_git_hash:
                        return False, (
                            f"⚠️ 版本冲突：快照记录为 {project['git_hash'][:7]}，"
                            f"当前为 {current_git_hash[:7]}。"
                            f"请确认 Git 分支或使用 git checkout 回退到记录版本。"
                        )
            
            messages = []

            # 2. 重置孤儿任务
            # 安全保护：仅重置 'in_progress' 状态的任务，completed/failed/blocked/pending 不受影响
            if reset_in_progress:
                cursor = conn.cursor()

                # 2a. 记录恢复前的状态分布（用于验证和日志）
                status_rows = cursor.execute("""
                    SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status
                """).fetchall()
                status_before = {row['status']: row['cnt'] for row in status_rows}

                # 2b. 严格限制：只重置 in_progress 状态
                # SQL WHERE 子句明确限定，不会影响到 completed/failed/blocked/pending
                cursor.execute("""
                    UPDATE tasks
                    SET status = 'pending',
                        owner = NULL,
                        started_at = NULL,
                        version = version + 1
                    WHERE status = 'in_progress'
                """)
                reaped_count = cursor.rowcount
                conn.commit()

                # 2c. 验证：确保 completed 任务数量没有变化
                status_rows_after = cursor.execute("""
                    SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status
                """).fetchall()
                status_after = {row['status']: row['cnt'] for row in status_rows_after}

                completed_before = status_before.get('completed', 0)
                completed_after = status_after.get('completed', 0)

                if completed_before != completed_after:
                    # 严重错误：completed 任务数量发生了变化
                    return False, (
                        f"CRITICAL ERROR: completed 任务数量异常变化！"
                        f"恢复前: {completed_before}, 恢复后: {completed_after}. "
                        f"请立即检查数据库完整性。"
                    )

                messages.append(
                    f"恢复完成: {reaped_count} 个孤儿任务已重置 | "
                    f"completed={completed_after}, pending={status_after.get('pending', 0)}, "
                    f"failed={status_after.get('failed', 0)}, blocked={status_after.get('blocked', 0)}"
                )
            
            # 3. 检测循环依赖
            cycles = self.detect_circular_dependencies()
            if cycles:
                cycle_str = ", ".join([" -> ".join(c) for c in cycles])
                messages.append(f"⚠️ 检测到 {len(cycles)} 个循环依赖: {cycle_str}")
            
            return True, "; ".join(messages) if messages else "无需要恢复的任务"
    
    # ==================== 知识库操作 ====================
    
    def add_knowledge(
        self, 
        project_id: str, 
        decision: str, 
        topic: Optional[str] = None,
        rationale: Optional[str] = None,
        context_tags: Optional[List[str]] = None,
        task_id: Optional[str] = None
    ) -> int:
        """
        添加知识库记录。
        
        Args:
            project_id: 项目 ID
            decision: 决策内容
            topic: 主题
            rationale: 决策理由
            context_tags: 上下文标签列表
            task_id: 关联任务 ID
            
        Returns:
            int: 新记录 ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_base 
                (project_id, topic, decision, rationale, context_tags, task_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id, topic, decision, rationale,
                json.dumps(context_tags) if context_tags else None,
                task_id
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_knowledge(
        self, 
        project_id: str, 
        topic: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        查询知识库记录。
        
        Args:
            project_id: 项目 ID
            topic: 可选的主题过滤
            limit: 返回记录数限制
            
        Returns:
            List[Dict]: 知识记录列表
        """
        with self._get_connection() as conn:
            query = "SELECT * FROM knowledge_base WHERE project_id = ?"
            params = [project_id]
            
            if topic:
                query += " AND topic = ?"
                params.append(topic)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                if d.get('context_tags'):
                    d['context_tags'] = json.loads(d['context_tags'])
                results.append(d)
            return results
    
    # ==================== Team 管理 ====================
    
    def register_team(
        self, 
        team_id: str, 
        project_id: str, 
        name: str,
        members: List[Dict[str, Any]]
    ) -> bool:
        """
        注册 Agent Team。
        
        Args:
            team_id: 团队唯一标识
            project_id: 所属项目 ID
            name: 团队名称
            members: 成员列表 [{"name": str, "role": str, "pid": int}]
            
        Returns:
            bool: 是否注册成功
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO teams (team_id, project_id, name)
                    VALUES (?, ?, ?)
                """, (team_id, project_id, name))
                
                for member in members:
                    conn.execute("""
                        INSERT INTO team_members 
                        (member_id, team_id, name, role, pid)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        f"{team_id}_{member['name']}",
                        team_id,
                        member['name'],
                        member.get('role', 'member'),
                        member.get('pid')
                    ))
                
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def update_team_heartbeat(self, team_id: str):
        """更新团队心跳时间戳。"""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE team_members 
                SET last_heartbeat = ?
                WHERE team_id = ?
            """, (datetime.now().isoformat(), team_id))
            conn.commit()
    
    def get_active_teams(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取活跃的团队列表。"""
        with self._get_connection() as conn:
            query = "SELECT * FROM teams WHERE status = 'active'"
            params = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
    
    # ==================== 工具方法 ====================
    
    @staticmethod
    def get_current_git_hash() -> Optional[str]:
        """获取当前 Git commit hash。"""
        try:
            return subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取项目统计信息。
        
        Returns:
            Dict: 包含任务统计、进度百分比、团队数量等信息
        """
        with self._get_connection() as conn:
            stats = {
                'total_tasks': 0,
                'completed_tasks': 0,
                'in_progress_tasks': 0,
                'pending_tasks': 0,
                'blocked_tasks': 0,
                'failed_tasks': 0,
                'progress_percent': 0.0,
                'teams': 0,
                'knowledge_entries': 0
            }
            
            # 任务统计
            query = """
                SELECT status, COUNT(*) as count 
                FROM tasks
                {where}
                GROUP BY status
            """
            where_clause = f"WHERE project_id = '{project_id}'" if project_id else ""
            rows = conn.execute(query.format(where=where_clause)).fetchall()
            
            for row in rows:
                status = row['status']
                count = row['count']
                stats['total_tasks'] += count
                
                if status == 'completed':
                    stats['completed_tasks'] = count
                elif status == 'in_progress':
                    stats['in_progress_tasks'] = count
                elif status == 'pending':
                    stats['pending_tasks'] = count
                elif status == 'blocked':
                    stats['blocked_tasks'] = count
                elif status == 'failed':
                    stats['failed_tasks'] = count
            
            # 计算进度百分比
            if stats['total_tasks'] > 0:
                stats['progress_percent'] = round(
                    (stats['completed_tasks'] / stats['total_tasks']) * 100, 1
                )
            
            # 团队数量
            query = "SELECT COUNT(*) as count FROM teams"
            params = []
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            row = conn.execute(query, params).fetchone()
            stats['teams'] = row['count']
            
            # 知识记录数
            query = "SELECT COUNT(*) as count FROM knowledge_base"
            params = []
            if project_id:
                query += " WHERE project_id = ?"
                params.append(project_id)
            row = conn.execute(query, params).fetchone()
            stats['knowledge_entries'] = row['count']
            
            return stats


# ==================== 便捷函数 ====================

def create_demo_project(db_path: str = ".state/project_storage.db"):
    """创建示例项目用于测试。"""
    storage = SkillStorage(db_path)
    
    # 创建项目
    git_hash = storage.get_current_git_hash()
    storage.create_project("demo", "演示项目", git_hash)
    
    # 使用新的 create_task 方法创建任务
    tasks = [
        ("task-001", "初始化数据库", "创建核心表结构", "high"),
        ("task-002", "实现用户认证", "JWT 登录注册", "medium"),
        ("task-003", "编写单元测试", "核心功能测试", "medium"),
        ("task-004", "部署到生产环境", "CI/CD 配置", "high"),
    ]
    
    for task_id, title, desc, priority in tasks:
        storage.create_task(task_id, "demo", title, desc, priority)
    
    # 设置依赖: task-004 依赖 task-001, task-002, task-003
    storage.add_task_dependency("task-004", "task-001")
    storage.add_task_dependency("task-004", "task-002")
    storage.add_task_dependency("task-004", "task-003")
    
    print(f"示例项目已创建: {db_path}")
    print(f"Git hash: {git_hash}")
    print(f"可执行任务: {[t['task_id'] for t in storage.get_ready_tasks('demo')]}")
    
    # 显示统计信息
    stats = storage.get_stats("demo")
    print(f"\n项目统计:")
    print(f"  总任务: {stats['total_tasks']}")
    print(f"  待处理: {stats['pending_tasks']}")
    print(f"  进度: {stats['progress_percent']}%")


if __name__ == "__main__":
    create_demo_project()
