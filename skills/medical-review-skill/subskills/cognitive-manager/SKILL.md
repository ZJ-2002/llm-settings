---
name: cognitive-manager
version: "2.5.1"
description: "认知调度员 - 协调19个模块的协同工作，实现错误自动回溯修正和全局一致性维护"
---

# 认知调度员 (Cognitive Manager) v2.5.1

## 功能定位

协调19个模块的协同工作，实现错误自动回溯修正和全局一致性维护。

## 核心组件

### 1. 全局状态监控器 (Global State Monitor)

维护综述项目的全局状态，类似手术室的中央监护系统。

### 2. 依赖关系图谱 (Dependency Graph)

定义模块间的输入输出和依赖关系。

### 3. 错误回溯引擎 (Error Rollback Engine)

当发现上游错误时，自动触发回溯和修正。

### 4. 一致性检查器 (Consistency Checker)

检查跨模块的数据、逻辑和引用一致性。

## 配置文件

- config.json: 全局配置
- dependencies.yaml: 依赖关系定义

**版本**: 2.5.1
