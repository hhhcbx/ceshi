# Ontology / RAG Learning Path

## 先建立概念边界

TrustGraph 里可以把 RAG 分成三层理解：

1. **Document RAG**
   - 输入：文档 chunk 和向量。
   - 检索：语义相似度。
   - 输出：基于召回文本的答案。
   - 适合先体验基本问答效果。

2. **Graph RAG**
   - 输入：实体、关系、三元组、provenance。
   - 检索：从问题 grounding 到实体，再扩展子图和路径。
   - 输出：基于图结构和来源证据的答案。
   - 适合观察“答案为什么这么来”。

3. **Ontology / OntologyRAG**
   - 输入：领域 class、property、关系约束、schema。
   - 作用：指导抽取、规范图谱、让查询更可控。
   - 目标：让 RAG 具备领域结构，而不仅是文本相似度。

## 演示时重点看什么

### 1. Ontology Workbench

关注：

- class 层级。
- property 定义。
- class 与 property 的关系。
- 导入/导出 Turtle 或 OWL。
- 是否能把样本文档里的概念抽象成领域 schema。

建议思考：

- `Belgian beer` 文档中，哪些是 class？
  - Beer
  - Brewery
  - Monastery
  - Yeast
  - FermentationMethod
- 哪些是 instance？
  - Chimay
  - Westvleteren
  - Oude Geuze
- 哪些是 property？
  - brewedBy
  - usesYeast
  - hasFermentationMethod
  - locatedIn

### 2. Document Ingestion

关注：

- 文档进入 library 后如何提交到 flow。
- chunk 如何生成。
- 文档 metadata 是否进入后续图谱。
- 处理完成后是否出现 entities、triples、provenance。

### 3. Graph Explorer

关注：

- 节点是否对应实体。
- 边是否对应关系。
- 搜索结果是否能从语义入口扩展到邻居节点。
- 点击节点是否能看到属性和来源。

### 4. Graph RAG Query

关注 explainability events：

- Question：原始问题。
- Grounding：问题被映射到哪些概念。
- Exploration：系统探索了哪些实体/边。
- Focus：哪些边被选入最终推理上下文。
- Synthesis：LLM 如何基于图上下文生成答案。

### 5. SPARQL / Graph 查询

CLI 可先从 help 开始：

```bash
tg-invoke-sparql-query --help
tg-query-graph --help
tg-show-graph --help
```

建议先做：

```sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
}
LIMIT 20
```

然后逐步收窄到 `rdf:type`、`rdfs:label`、具体实体。

## 推荐问题

### Ontology 设计类

```text
根据样本文档，哪些概念应该设计成 ontology classes？
哪些关系应该设计成 ontology properties？
哪些实体应该作为 instances 而不是 classes？
```

### Graph RAG 类

```text
根据知识图谱，解释 Belgian beer 中修道院、酵母和发酵方式之间的关系。
```

```text
根据知识图谱，解释 pre-modern European trade routes 中城市、商品、贸易路线和地缘瓶颈之间的关系。
```

### Document RAG 对照类

```text
只根据文档内容，总结 Belgian beer 的核心主题。
```

然后用 Graph RAG 问相同问题，对比：

- 是否出现结构化关系。
- 是否有 provenance。
- 是否能解释检索路径。

## 学习顺序

1. 先跑 Document RAG，理解最基础问答。
2. 再跑 Graph RAG，观察答案背后的实体和关系。
3. 进入 Ontology Workbench，尝试把实体和关系提升为 schema。
4. 回到源码，看 extraction、ontology query、retrieval 的实现。
5. 最后尝试导入自己的 Turtle/OWL，验证 ontology 对抽取和查询的影响。

