# TrustGraph Source Map

本笔记基于临时阅读的 `trustgraph-ai/trustgraph` 源码整理，帮助把 demo 功能和源码目录对应起来。

## Monorepo 包结构

- `trustgraph/`
  - 顶层 Python 包，README 指向官网。
- `trustgraph-base/`
  - API schema、消息类型、基础客户端和公共能力。
- `trustgraph-cli/`
  - 命令行工具。
  - demo kit 主要调用这里的脚本。
- `trustgraph-flow/`
  - 后端处理器、retrieval、gateway、storage、query、bootstrap 等核心服务。
- `trustgraph-mcp/`
  - MCP server。
- `trustgraph-ocr/`
  - OCR/PDF 解码。
- `trustgraph-unstructured/`
  - 非结构化文档解析。
- `trustgraph-vertexai/`、`trustgraph-bedrock/`
  - 云厂商模型集成。
- `trustgraph-embeddings-hf/`
  - HuggingFace embeddings 集成。

## CLI 入口

`trustgraph-cli/pyproject.toml` 注册大量 `tg-*` 命令，重点包括：

- `tg-verify-system-status`
- `tg-load-sample-documents`
- `tg-invoke-llm`
- `tg-invoke-document-rag`
- `tg-invoke-graph-rag`
- `tg-invoke-sparql-query`
- `tg-query-graph`
- `tg-show-graph`
- `tg-show-extraction-provenance`
- `tg-list-explain-traces`
- `tg-show-explain-trace`

## 样本文档

位置：

```text
trustgraph-cli/trustgraph/cli/sample_documents/
```

文件：

- `recipes.md`
- `belgian-beer.md`
- `trade-routes-europe.md`
- `history-of-pets.md`
- `mil-fortifications-america-19th-c.md`
- `metadata.json`

加载逻辑：

```text
trustgraph-cli/trustgraph/cli/load_sample_documents.py
```

该脚本读取 metadata 和 markdown/pdf 内容，通过 `Api(...).library().add_document(...)`
写入 TrustGraph library。

## Document RAG

CLI：

```text
trustgraph-cli/trustgraph/cli/invoke_document_rag.py
```

服务实现重点：

```text
trustgraph-flow/trustgraph/retrieval/document_rag/
```

重点理解：

- query 如何进入 flow。
- collection 如何选择。
- doc limit / fetch limit 如何影响召回。
- explainability 如何输出 Question、Exploration、Synthesis。

## Graph RAG

CLI：

```text
trustgraph-cli/trustgraph/cli/invoke_graph_rag.py
```

服务实现重点：

```text
trustgraph-flow/trustgraph/retrieval/graph_rag/
```

重点理解：

- grounding：问题如何映射到图谱概念。
- exploration：如何扩展实体与边。
- focus：如何选择最重要的图边。
- synthesis：如何把图上下文交给 LLM。
- explainability：如何把推理事件暴露出来。

## Ontology 相关源码入口

重点目录：

```text
trustgraph-flow/trustgraph/query/ontology/
```

从文件名看，核心包括：

- ontology cache。
- ontology query service。
- SPARQL/Cassandra 查询。

还应结合：

```text
trustgraph-flow/trustgraph/extract/
trustgraph-flow/trustgraph/cores/
trustgraph-base/trustgraph/schema/
trustgraph-base/trustgraph/provenance/
```

学习顺序建议：

1. 先读 CLI：看用户命令如何组织参数。
2. 再读 `trustgraph.api`：看客户端如何请求 gateway/flow。
3. 再读 retrieval 服务：看 Document RAG 与 Graph RAG 差异。
4. 最后读 ontology query/extract/provenance：理解 ontology 如何影响结构化知识。

## 运行部署入口

官方推荐：

```bash
npx @trustgraph/config
```

生成：

- `deploy.zip`
- `INSTALLATION.md`

部署包中会包含：

- `docker-compose.yaml`
- `trustgraph/config.json`
- Grafana/Prometheus/Loki/Garage 等配置。

官方 Workbench 默认端口：

- UI: `8888`
- API Gateway: `8088`
- Grafana: `3000`

