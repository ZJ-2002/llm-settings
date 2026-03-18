---
name: lazy-anchor-rag
description: 硬锚点动态加载与RAG集成架构。解决大规模文献综述中的上下文窗口限制问题，实现按需加载证据锚点。
version: "1.0.0"
---

# Lazy Anchor RAG 架构

## 概述

在大型综述项目（100-200篇参考文献，500+知识点）中，传统"全量锚点加载"模式会导致：
- 上下文窗口溢出
- 处理速度极慢
- 检索噪音增加

Lazy Anchor RAG架构通过**分层存储 + 动态检索 + 按需加载**解决上述问题。

---

## 核心概念

### 锚点分层体系

```
锚点库 (Anchor Repository)
│
├── 层级1: 核心论点锚点 (Critical Path Anchors)
│   ├── 定义: 支撑综述核心结论的30-50个关键证据
│   ├── 加载策略: 常驻内存
│   └── 验证要求: 100%人工核对
│
├── 层级2: 章节支撑锚点 (Section Support Anchors)
│   ├── 定义: 各章节主要论述的支撑证据
│   ├── 加载策略: 章节切换时加载
│   └── 验证要求: 抽检50%
│
├── 层级3: 背景补充锚点 (Background Anchors)
│   ├── 定义: 背景信息、引言引用
│   ├── 加载策略: 按需检索，用完释放
│   └── 验证要求: AI提取即可
│
└── 层级4: 方法学锚点 (Methodology Anchors)
    ├── 定义: 研究设计、统计方法描述
    ├── 加载策略: 仅方法学讨论时加载
    └── 验证要求: 关键方法人工核对
```

### 动态加载策略

```python
class LazyAnchorLoader:
    """懒加载锚点管理器"""
    
    def __init__(self):
        self.critical_anchors = []      # 常驻
        self.section_anchors = {}       # 章节缓存
        self.retrieval_index = None     # 向量索引
        
    def get_relevant_anchors(self, query_context, current_section):
        """
        根据查询上下文获取相关锚点
        
        策略:
        1. 始终包含核心论点锚点
        2. 包含当前章节锚点
        3. 向量检索获取语义相关锚点
        4. 总量控制在上下文限制内
        """
        anchors = []
        
        # 1. 添加核心论点锚点（必须）
        anchors.extend(self.critical_anchors)
        
        # 2. 添加当前章节锚点
        if current_section in self.section_anchors:
            anchors.extend(self.section_anchors[current_section])
        
        # 3. 向量检索相关锚点
        related = self.vector_search(query_context, top_k=10)
        anchors.extend(related)
        
        # 4. 去重并排序
        anchors = self.deduplicate_and_rank(anchors)
        
        # 5. 截断至上下文限制
        return self.truncate_to_context_limit(anchors)
    
    def vector_search(self, query, top_k=10):
        """基于语义相似度的锚点检索"""
        query_embedding = self.embed(query)
        results = self.retrieval_index.search(query_embedding, k=top_k)
        return [self.load_anchor(r.id) for r in results]
```

---

## 架构组件

### 1. 向量存储层

```yaml
存储架构:
  主存储:
    类型: ChromaDB / Pinecone / Weaviate
    内容: 锚点原文快照的向量嵌入
    维度: 1536 (OpenAI) / 1024 (Claude)
    
  元数据:
    - anchor_id: 唯一标识
    - viewpoint_id: 关联观点
    - paper_id: 来源文献
    - section: 所属章节
    - level: 锚点层级 (1-4)
    - verification_status: 验证状态
    - key_terms: 关键词列表
    
  索引策略:
    - 按section分片
    - 按level标记优先级
    - 按verification_status过滤
```

### 2. 检索优化

```python
class AnchorRetriever:
    """锚点检索器，支持多策略检索"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.keyword_index = KeywordIndex()
        self.citation_graph = CitationGraph()
    
    def hybrid_search(self, query, filters=None):
        """
        混合检索策略
        
        1. 向量语义检索（权重60%）
        2. 关键词匹配（权重30%）
        3. 引用关系扩展（权重10%）
        """
        # 向量检索
        vector_results = self.vector_store.similarity_search(
            query, 
            k=20,
            filter=filters
        )
        
        # 关键词检索
        keyword_results = self.keyword_index.search(
            self.extract_keywords(query),
            k=10
        )
        
        # 引用扩展
        cited_papers = self.extract_citations(query)
        citation_results = self.citation_graph.get_related_anchors(
            cited_papers,
            k=5
        )
        
        # 融合排序
        return self.reciprocal_rank_fusion([
            vector_results,
            keyword_results,
            citation_results
        ])
```

### 3. 缓存管理

```python
class AnchorCache:
    """多级缓存系统"""
    
    def __init__(self):
        self.l1_cache = {}      # 核心锚点，常驻
        self.l2_cache = LRUCache(maxsize=100)  # 章节锚点
        self.l3_cache = LRUCache(maxsize=50)   # 检索结果
    
    def get(self, anchor_id, context):
        # L1: 核心锚点
        if anchor_id in self.l1_cache:
            return self.l1_cache[anchor_id]
        
        # L2: 当前章节缓存
        if context.section in self.l2_cache:
            section_cache = self.l2_cache[context.section]
            if anchor_id in section_cache:
                return section_cache[anchor_id]
        
        # L3: 检索缓存
        cache_key = f"{context.section}:{anchor_id}"
        if cache_key in self.l3_cache:
            return self.l3_cache[cache_key]
        
        # 缓存未命中，从存储加载
        anchor = self.load_from_storage(anchor_id)
        self.put(context.section, anchor_id, anchor)
        return anchor
```

---

## 与综述工作流集成

### STEP 3-4: 证据综合阶段

```markdown
## 证据综合流程（RAG增强版）

### 阶段1: 锚点入库
1. 提取观点时生成锚点
2. 计算向量嵌入
3. 存入向量数据库
4. 标记层级（根据重要性）

### 阶段2: 知识图谱构建
1. 基于向量相似度发现关联
2. 构建观点-锚点-文献网络
3. 识别关键路径（核心论点链）

### 阶段3: 动态综合
撰写时每段遵循：
```
1. 确定论述主题
2. 检索相关锚点（向量+关键词）
3. 加载锚点原文快照
4. 综合论述
5. 插入引用标注
```
```

### STEP 5: 大纲设计阶段

```markdown
## 大纲设计时的锚点规划

### 核心论点识别
通过向量聚类识别核心论点：
```python
def identify_critical_anchors(anchor_embeddings):
    """识别核心论点锚点"""
    # 使用聚类发现主题簇
    clusters = clustering(anchor_embeddings, n_clusters=5-8)
    
    # 每个簇选择最中心的锚点作为核心
    critical_anchors = []
    for cluster in clusters:
        center = find_centroid(cluster)
        critical_anchors.append(center)
    
    return critical_anchors
```

### 章节锚点分配
```yaml
章节锚点分配:
  Introduction:
    level_1: 2-3个（研究背景核心）
    level_2: 5-8个
    
  Epidemiology:
    level_1: 3-5个（关键流行病学数据）
    level_2: 10-15个
    
  Mechanisms:
    level_1: 5-8个（核心机制）
    level_2: 15-20个
    
  Diagnosis:
    level_1: 3-5个（诊断标准）
    level_2: 8-12个
    
  Management:
    level_1: 5-8个（治疗推荐）
    level_2: 15-25个
```

### STEP 6-7: 撰写阶段

```markdown
## 章节撰写时的锚点加载

### 写作前准备
```python
def prepare_section_writing(section_name):
    """准备章节撰写环境"""
    
    # 1. 加载该章节的核心锚点（常驻）
    critical = load_anchors(
        section=section_name, 
        level=1
    )
    
    # 2. 加载该章节的支撑锚点（缓存）
    support = load_anchors(
        section=section_name, 
        level=2
    )
    
    # 3. 预加载引用关系
    citation_graph = load_citation_graph(section_name)
    
    return WritingContext(
        critical_anchors=critical,
        support_anchors=support,
        citation_graph=citation_graph,
        retriever=AnchorRetriever()
    )
```

### 段落写作流程
```python
def write_paragraph(topic, context):
    """撰写单段"""
    
    # 1. 检索相关锚点
    relevant_anchors = context.retriever.hybrid_search(
        query=topic,
        section=context.section_name,
        existing_citations=context.used_citations
    )
    
    # 2. 加载锚点原文（按需）
    anchor_snapshots = []
    for anchor in relevant_anchors[:5]:  # 限制数量
        snapshot = lazy_load(anchor.id)
        anchor_snapshots.append(snapshot)
    
    # 3. 生成段落（带锚点上下文）
    paragraph = generate_with_anchors(
        topic=topic,
        anchors=anchor_snapshots,
        style="academic"
    )
    
    # 4. 更新已使用引用
    context.used_citations.update(extract_citations(paragraph))
    
    return paragraph
```

### STEP 8: 投稿前检查

```markdown
## 锚点一致性校验

### 校验项目
1. **引用存在性**
   - 所有引用是否都有对应锚点
   - 锚点是否完整（原文快照+元数据）

2. **一致性校验**
   - 正文表述与锚点原文是否一致
   - 多次引用同一文献是否表述一致

3. **覆盖率检查**
   - 核心论点是否都有锚点支撑
   - 高确定性证据是否有验证锚点

### 校验脚本
```python
def verify_anchor_integrity(review_draft, anchor_repo):
    """校验锚点完整性"""
    issues = []
    
    # 提取所有引用
    citations = extract_all_citations(review_draft)
    
    for citation in citations:
        # 检查锚点存在
        anchor = anchor_repo.get_by_citation(citation)
        if not anchor:
            issues.append({
                'type': 'missing_anchor',
                'citation': citation,
                'severity': 'high'
            })
            continue
        
        # 检查锚点完整性
        if not anchor.snapshot:
            issues.append({
                'type': 'incomplete_anchor',
                'citation': citation,
                'severity': 'medium'
            })
        
        # 检查验证状态
        if anchor.level == 1 and anchor.verification_status != 'verified':
            issues.append({
                'type': 'unverified_critical_anchor',
                'citation': citation,
                'severity': 'high'
            })
    
    return issues
```
```

---

## 性能优化

### 上下文预算分配

```python
CONTEXT_BUDGET = 100000  # tokens

BUDGET_ALLOCATION = {
    'system_prompt': 2000,
    'writing_instructions': 3000,
    'critical_anchors': 15000,      # 核心锚点预留
    'section_anchors': 20000,       # 章节锚点预留
    'retrieved_anchors': 30000,     # 动态检索预留
    'working_memory': 25000,        # 写作缓冲区
    'response_buffer': 5000         # 回复预留
}
```

### 锚点压缩策略

```python
def compress_anchor(anchor, target_length=100):
    """压缩锚点原文快照"""
    
    if len(anchor.snapshot) <= target_length:
        return anchor
    
    # 保留关键信息：数值、P值、CI
    preserved_info = extract_key_data(anchor.snapshot)
    
    # 压缩为结构化摘要
    compressed = f"""
    [来源: {anchor.paper_id}]
    [关键发现: {preserved_info.finding}]
    [效应量: {preserved_info.effect_size}]
    [原文片段: {anchor.snapshot[:target_length]}...]
    """
    
    return anchor.copy_with_snapshot(compressed)
```

---

## 技术实现

### 完整配置示例

```yaml
# lazy-anchor-rag.yaml

vector_store:
  provider: chromadb
  path: ./anchor_vectors
  embedding_model: text-embedding-3-large
  
retrieval:
  hybrid_search: true
  vector_weight: 0.6
  keyword_weight: 0.3
  citation_weight: 0.1
  
  # 检索参数
  top_k: 15
  similarity_threshold: 0.75
  
cache:
  l1_size: 50       # 核心锚点
  l2_size: 100      # 章节缓存
  l3_size: 50       # 检索缓存
  ttl: 3600         # 缓存过期时间（秒）

anchor_levels:
  level_1:
    name: "critical"
    max_count: 50
    verification_required: true
    load_strategy: "always"
  
  level_2:
    name: "section"
    max_count: 200
    verification_required: false
    load_strategy: "section_switch"
  
  level_3:
    name: "background"
    max_count: 500
    verification_required: false
    load_strategy: "on_demand"

monitoring:
  log_retrieval: true
  track_cache_hit_rate: true
  alert_on_missing_anchor: true
```

---

## 预期效果

| 指标 | 传统全量加载 | Lazy Anchor RAG | 改进 |
|------|-------------|-----------------|------|
| 上下文使用量 | 150K+ tokens | 50-70K tokens | ↓60% |
| 平均响应时间 | 45s | 15s | ↓67% |
| 检索精准度 | 60% | 85% | ↑42% |
| 幻觉发生率 | 12% | 4% | ↓67% |
| 支持文献规模 | <50篇 | 200+篇 | ↑300% |

---

*版本: 1.0.0*
*更新日期: 2026-03-12*