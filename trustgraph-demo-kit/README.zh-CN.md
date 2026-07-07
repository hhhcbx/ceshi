# TrustGraph Ontology / RAG Demo Kit

这个目录是为了在受限网络环境下学习和复现
[trustgraph-ai/trustgraph](https://github.com/trustgraph-ai/trustgraph)
而整理的中文 demo 包。重点放在你最关注的 **Ontology、OntologyRAG、Graph RAG、Document RAG**。

> 当前仓库不是 TrustGraph 源码仓库。本目录提供的是运行、演示、学习脚本和笔记。TrustGraph
> 官方推荐通过配置工具生成 Docker/Podman Compose 部署包，而不是直接从源码启动所有服务。

## 你会得到什么

- 一套可复制到本地或服务器执行的 TrustGraph 部署脚本。
- DeepSeek/OpenAI-compatible LLM 后端配置模板。
- 以 ontology 为重点的演示路线：
  1. 启动 TrustGraph。
  2. 验证系统健康。
  3. 加载样本文档。
  4. 处理文档进入默认 flow。
  5. 查看 ontology / graph / provenance。
  6. 分别体验 Document RAG、Graph RAG、Ontology 相关查询。
- 源码学习笔记，帮助你把功能体验和 TrustGraph 内部实现对应起来。

## 为什么 ontology 是 RAG 的关键部分

在 TrustGraph 里，RAG 不只是“向量检索 + LLM 总结”。

- **Document RAG** 更接近传统语义检索：文档被切块、向量化、召回，然后交给 LLM 生成答案。
- **Graph RAG** 会利用实体、关系、三元组和 provenance，让答案可以追踪到图结构与来源。
- **Ontology / OntologyRAG** 更进一步：ontology 定义领域概念、类型、关系和约束，让系统知道“什么是什么”“哪些关系是合法/重要的”，从而让抽取、图谱构建和检索更稳定。

所以 ontology 不是可有可无的文档标签，而是让 RAG 从“相似文本召回”走向“结构化领域理解”的核心层。

## 运行前提

官方 Docker/Podman Compose 教程要求大致如下：

- Python 3.11+
- Node.js/npm
- Docker Engine + Compose，或 Podman + podman-compose
- 约 12GB+ 内存
- 8 CPU 推荐
- 一个可用 LLM 后端

当前云端机器已有 Python 和 Node，但没有 Docker/Podman，因此完整容器 demo 需要继续尝试安装容器运行环境，或在你的本地/服务器运行。

## DeepSeek 配置

DeepSeek 提供 OpenAI-compatible API。TrustGraph 文档支持 OpenAI-compatible
后端，因此建议按 OpenAI 模式配置：

```bash
export OPENAI_TOKEN="你的 DeepSeek API Key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

如果你暂时不想提供 key，可以先复制 `.env.example`，把 key 留空，最后自己补。

```bash
cp trustgraph-demo-kit/.env.example .env
```

> 注意：不要把真实 API key 提交到 GitHub。

## 建议演示顺序

### 1. 生成部署包

```bash
trustgraph-demo-kit/scripts/generate-deploy.sh
```

该脚本会调用官方工具：

```bash
npx @trustgraph/config
```

生成 `deploy.zip` 和 `INSTALLATION.md`。

### 2. 启动服务

进入部署包解压目录后执行：

```bash
trustgraph-demo-kit/scripts/start.sh
```

默认会导出：

- `IAM_BOOTSTRAP_TOKEN`
- `GF_SECURITY_ADMIN_PASSWORD`
- `TRUSTGRAPH_TOKEN`
- `OPENAI_TOKEN`
- `OPENAI_BASE_URL`

### 3. 健康检查

```bash
trustgraph-demo-kit/scripts/verify.sh
```

预期核心命令：

```bash
tg-verify-system-status
```

### 4. 加载样本文档

```bash
trustgraph-demo-kit/scripts/load-samples.sh
```

样本文档在 TrustGraph CLI 包内，包括：

- West Country recipes
- Belgian beer
- Pre-modern European trade routes
- History of pets
- 19th century American coastal fortifications

### 5. 重点观察 ontology / graph

建议先从 UI 操作：

- Workbench: `http://localhost:8888`
- API Key 登录：使用 `IAM_BOOTSTRAP_TOKEN`
- 进入 `Ontology Workbench`
- 进入 `Graph Explorer`
- 进入 `Graph RAG Query`

再用 CLI 辅助观察：

```bash
tg-show-graph
tg-query-graph --help
tg-invoke-sparql-query --help
tg-show-extraction-provenance --help
```

### 6. RAG 查询

Document RAG：

```bash
trustgraph-demo-kit/scripts/query-document-rag.sh
```

Graph RAG：

```bash
trustgraph-demo-kit/scripts/query-graph-rag.sh
```

Ontology 相关问题建议：

```text
这些样本文档中有哪些核心实体类型？
Belgian beer 文档里，修道院、酵母、发酵方式之间有什么关系？
Pre-modern European trade routes 中，城市、商品、贸易路线之间是什么关系？
哪些概念可以被抽象成 ontology class，哪些更适合作为 instance？
```

## 阶段记录

- `notes/stage-1-demo-kit.md`：第 1 阶段，demo kit 与运行方案。
- `notes/ontology-learning-path.md`：ontology/RAG 学习路线。
- `notes/source-map.md`：TrustGraph 源码结构与重点文件。
- `artifacts/`：后续云端实跑日志、部署包摘要、截图说明等。

## 后续阶段计划

1. 第 1 阶段：完成本 demo kit，提交到 GitHub。
2. 第 2 阶段：尝试在云端安装容器环境、生成部署包并实跑；结果无论成功失败都写入 `artifacts/`。
3. 第 3 阶段：结合源码补充 ontology、Graph RAG、Document RAG 的学习笔记。

