# Ontology / RAG Source Deep Dive

本笔记聚焦 TrustGraph 源码中和 ontology、OntologyRAG、Graph RAG、Document RAG
最相关的路径。

## 1. 大图：Ontology 在 TrustGraph RAG 里的位置

TrustGraph 里至少有三条相互关联的 RAG 路线：

```text
Document RAG
  question -> concepts -> document embeddings -> chunks -> optional rerank -> LLM answer

Graph RAG
  question -> concepts -> graph entity embeddings -> seed entities
           -> graph traversal -> edge rerank/focus -> LLM answer

Ontology / OntoRAG
  ontology config -> classes/properties/domain/range -> ontology embeddings
                  -> select ontology subset for text/question
                  -> ontology-conformant extraction or SPARQL/Cypher query
```

核心区别：

- Document RAG 检索的是文本 chunk。
- Graph RAG 检索和遍历的是实体/边。
- OntologyRAG 用 class/property/schema 约束“可以抽取什么、怎么查询、什么关系有效”。

## 2. Ontology 数据模型

源码：

```text
trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py
```

核心结构：

- `OntologyClass`
  - `uri`
  - `labels`
  - `comment`
  - `subclass_of`
  - `equivalent_classes`
  - `disjoint_with`
- `OntologyProperty`
  - `uri`
  - `type`
  - `labels`
  - `comment`
  - `domain`
  - `range`
  - `inverse_of`
  - cardinality 相关字段
- `Ontology`
  - `classes`
  - `object_properties`
  - `datatype_properties`

`validate_structure()` 会检查：

- class 继承是否循环。
- property domain 是否存在。
- object property range 是否是已知 class。
- disjoint class 是否存在。

学习重点：

- `domain` / `range` 是 ontology 对抽取质量影响最大的字段之一。
- `subClassOf` 会影响 domain/range 校验，因为子类可被视为父类的一种。
- `inverseOf`、`equivalentClass` 等会影响查询侧扩展和推理规则。

## 3. Ontology 配置如何进入抽取 pipeline

源码：

```text
trustgraph-flow/trustgraph/extract/kg/ontology/extract.py
```

关键类：

```python
class Processor(FlowProcessor)
```

初始化时注册：

- `ConsumerSpec(name="input", schema=Chunk)`
- `PromptClientSpec`
- `EmbeddingsClientSpec`
- `ProducerSpec(name="triples", schema=Triples)`
- `ProducerSpec(name="entity-contexts", schema=EntityContexts)`
- `register_config_handler(..., types=["ontology"])`

这说明 ontology 抽取处理器不是离线脚本，而是 flow 里的一个处理节点：

1. 接收 chunk。
2. 从 workspace config 监听 ontology 更新。
3. 按 workspace 保存 ontology loader。
4. 按 flow 初始化 ontology embedder/vector store/selector。
5. 输出 triples 和 entity contexts。

## 4. Ontology 更新与重新 embedding

源码位置：

```text
Processor.on_ontology_config()
Processor.initialize_flow_components()
```

流程：

```text
config update
  -> 读取 config["ontology"]
  -> json.loads 每个 ontology
  -> OntologyLoader.update_ontologies()
  -> 如果 ontology 变更，清理对应 workspace 的 flow components
  -> 下次处理 chunk 时重新初始化并重新 embedding ontology 元素
```

这点很重要：如果你在 Workbench 里修改 ontology，理论上后续 chunk 处理会使用新的 ontology
embedding 与 selector。

## 5. Ontology 元素如何被 embedding

源码：

```text
trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py
```

`OntologyEmbedder._create_text_representation()` 会为每个 ontology 元素构造文本：

- element id
- labels
- comment/description
- class 的 `subclass_of`
- property 的 `domain` / `range`

然后批量调用 embedding service：

```text
classes -> embeddings
object properties -> embeddings
datatype properties -> embeddings
```

结果存入 `InMemoryVectorStore`，metadata 里保留：

- ontology id
- element type
- element id
- full definition
- embedding text

理解：

- ontology 不是只拿来展示的，它本身也被向量化。
- 文档 chunk 或问题会和 ontology 元素做相似度匹配，从而选择相关 schema 子集。

## 6. 文本如何选择相关 ontology subset

源码：

```text
trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py
```

核心流程：

```text
TextSegment list
  -> embed each segment
  -> search ontology vector store
  -> filter by similarity threshold
  -> group by ontology
  -> build OntologySubset
  -> resolve dependencies
```

`OntologySubset` 包含：

- relevant classes
- relevant object properties
- relevant datatype properties
- metadata
- relevance score

依赖补全很关键：

- 选中 class 后补父类。
- 选中 property 后补 domain/range class。

这避免 LLM 只看到一个孤立 property，却不知道该 property 的 subject/object 类型约束。

## 7. Ontology-conformant extraction

源码：

```text
trustgraph-flow/trustgraph/extract/kg/ontology/extract.py
trustgraph-flow/trustgraph/extract/kg/ontology/triple_converter.py
```

抽取流程：

```text
Chunk
  -> TextProcessor.process_chunk()
  -> OntologySelector.select_ontology_subset()
  -> build_extraction_variables()
  -> prompt id: extract-with-ontologies
  -> parse_extraction_response()
  -> TripleConverter.convert_all()
  -> emit triples + entity contexts
```

prompt 变量：

```python
{
    "text": chunk,
    "classes": ontology_subset.classes,
    "object_properties": ontology_subset.object_properties,
    "datatype_properties": ontology_subset.datatype_properties,
}
```

`TripleConverter` 做了三件非常重要的事：

1. entity -> `rdf:type` + `rdfs:label`
2. relationship -> object property triple
3. attribute -> datatype property triple

并且会校验：

- entity type 是否是 ontology 中已知 class。
- relationship 是否是已知 object property。
- attribute 是否是已知 datatype property。
- property domain/range 是否匹配。
- 子类是否满足父类约束。

这就是 ontology 对 RAG 质量的实质影响：它把 LLM 抽取的自由文本关系压回 schema。

## 8. Ontology triples 与 provenance

抽取处理器不仅输出文档中抽取出来的 triples，也会输出 ontology definition triples：

```text
content triples + ontology triples + provenance triples
```

provenance 相关源码：

```text
trustgraph-base/trustgraph/provenance/namespaces.py
trustgraph-base/trustgraph/provenance/triples.py
```

重要 named graph：

- `GRAPH_DEFAULT = ""`
  - 核心知识事实。
- `GRAPH_SOURCE = "urn:graph:source"`
  - 抽取来源、文档、chunk、subgraph provenance。
- `GRAPH_RETRIEVAL = "urn:graph:retrieval"`
  - 查询时 explainability：question、grounding、exploration、focus、synthesis。

Graph RAG 会通过 provenance 链路把选中的 edge 追溯回文档：

```text
edge -> subgraph -> chunk -> page/section -> document
```

这也是 TrustGraph 和普通向量 RAG 很不一样的地方。

## 9. OntoRAG 查询服务

源码：

```text
trustgraph-flow/trustgraph/query/ontology/query_service.py
```

主类：

```python
class OntoRAGQueryService(FlowProcessor)
```

处理流程：

```text
QueryRequest
  -> QuestionAnalyzer
  -> OntologyMatcherForQueries
  -> BackendRouter
  -> SPARQLGenerator or CypherGenerator
  -> SPARQLCassandraEngine or CypherExecutor
  -> AnswerGenerator
  -> QueryResponse
```

`QueryResponse` 不只返回 answer，还包含：

- confidence
- execution_time
- question_analysis
- ontology_subsets
- query_route
- generated_query
- raw_results
- supporting_facts
- metadata

这说明 OntoRAG 查询天然适合学习和调试，因为它保留了中间结构。

## 10. QuestionAnalyzer

源码：

```text
trustgraph-flow/trustgraph/query/ontology/question_analyzer.py
```

问题类型：

- factual
- retrieval
- aggregation
- comparison
- relationship
- boolean
- process
- temporal
- spatial

它会提取：

- entities
- relationships
- constraints
- aggregations
- expected answer type
- keywords

这一步决定后面应该查 class、property、count、relationship 还是 ASK。

## 11. OntologyMatcherForQueries

源码：

```text
trustgraph-flow/trustgraph/query/ontology/ontology_matcher.py
```

它继承 extraction 侧的 `OntologySelector`，但为查询增强：

- relationship 问题：补充连接相关 class 的 object properties。
- retrieval 问题：补充 domain 在相关 class 上的 properties。
- aggregation 问题：补充 count/number 相关 datatype properties。
- 自动加入 inverse property。
- 自动加入同 domain 的 sibling properties。
- 添加推理规则：
  - subclass transitivity
  - equivalentClass symmetry
  - inverse property

这就是 OntologyRAG 查询相较普通 Graph RAG 的不同：它不是只从图上扩边，而是先用 ontology
选择“应该如何查”。

## 12. Backend routing

源码：

```text
trustgraph-flow/trustgraph/query/ontology/backend_router.py
```

支持后端：

- Cassandra -> SPARQL
- Neo4j -> Cypher
- Memgraph -> Cypher
- FalkorDB -> Cypher

默认 priority 策略会优先选配置中的 primary backend。adaptive 策略会根据问题和 ontology
复杂度打分。

本 demo 包生成的部署选择了 Cassandra，所以 ontology 查询路径应重点看 SPARQL。

## 13. SPARQL 生成与执行

源码：

```text
trustgraph-flow/trustgraph/query/ontology/sparql_generator.py
trustgraph-flow/trustgraph/query/ontology/sparql_cassandra.py
```

SPARQL generator 有两层：

1. 模板优先：
   - simple class query
   - property query
   - hierarchy query
   - count query
   - boolean ASK query
2. LLM fallback：
   - 如果模板不够，用 prompt service 生成 SPARQL。

Cassandra SPARQL engine 使用 rdflib Store 包装 Cassandra triple table：

```text
subject text
predicate text
object text
object_datatype text
object_language text
is_literal boolean
graph_id text
PRIMARY KEY ((subject), predicate, object)
```

它能把 triple pattern 转成 CQL，但 full scan 和 `ALLOW FILTERING` 在生产中要谨慎。

## 14. Graph RAG 对照

源码：

```text
trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py
```

Graph RAG 查询流程：

```text
query
  -> extract concepts
  -> embed concepts
  -> graph_embeddings_client.query() 得到 seed entities
  -> 从 triples store 查一跳/多跳边
  -> 过滤 RDF/RDFS/OWL schema predicate
  -> resolve labels
  -> cross-encoder rerank edge candidates
  -> focus selected edges
  -> trace source documents
  -> LLM synthesis
```

Graph RAG 的 explainability：

- Question
- Grounding
- Exploration
- Focus
- Synthesis

其中 Focus 是最值得观察的：它记录哪些 edge 被 cross-encoder 选入最终上下文。

## 15. Document RAG 对照

源码：

```text
trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py
```

Document RAG 查询流程：

```text
query
  -> extract concepts
  -> embed concepts
  -> doc_embeddings_client.query()
  -> fetch chunks from Garage
  -> optional cross-encoder rerank / MMR diversity
  -> LLM document_prompt
```

Document RAG 的 explainability：

- Question
- Grounding
- Exploration
- Focus only if reranker ran
- Synthesis

和 Graph RAG 的本质差异：

- Document RAG 的 Focus 是 selected chunks。
- Graph RAG 的 Focus 是 selected edges。

## 16. 建议你运行时怎么观察

### UI

1. `Ontology Workbench`
   - 看 class/property/domain/range。
2. `Document Ingestion`
   - 提交样本文档处理。
3. `Graph Explorer`
   - 搜索实体，展开邻居。
4. `Graph RAG Query`
   - 重点看 Focus event 和 source/provenance。

### CLI

```bash
tg-show-graph
tg-query-graph --help
tg-invoke-sparql-query --help
tg-show-extraction-provenance --help
tg-list-explain-traces
tg-show-explain-trace --help
```

### 对照问题

先问 Document RAG：

```text
Summarize the main topics in the Belgian beer document.
```

再问 Graph RAG：

```text
Using the knowledge graph, explain how monasteries, yeast, fermentation methods, and beer styles are related.
```

最后问 ontology 设计问题：

```text
Which concepts should be ontology classes, which should be object properties, and which should be datatype properties?
```

你要重点比较：

- Document RAG 给的是文本摘要。
- Graph RAG 给的是实体关系。
- Ontology 视角关注 schema 是否合理，以及抽取结果是否符合 domain/range。

