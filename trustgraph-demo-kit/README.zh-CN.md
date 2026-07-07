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
- Docker Engine + Compose，或 Podman + podman-compose
- 约 12GB+ 内存
- 8 CPU 推荐
- 一个可用 LLM 后端

你本地**不需要运行**：

```bash
npx @trustgraph/config
```

因为你的本地网络受限，我已经在云端替你生成好了官方部署包。后续操作直接从这个 ZIP 开始。

当前云端机器已有 Python 和 Node。第 2 阶段已尝试安装 Podman 并启动完整栈，但该云端容器缺少可用
`/dev/net/tun`/tun 内核支持，rootless Podman 无法创建 compose 网络。因此完整 UI/RAG demo
需要在你的本地或另一台支持 Docker/Podman 网络的服务器运行。

已经生成好的官方部署包在：

```text
trustgraph-demo-kit/artifacts/deploy-openai-deepseek-compatible.zip
```

云端尝试记录在：

```text
trustgraph-demo-kit/artifacts/stage-2-cloud-run.md
```

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

### 1. 下载并解压已经生成好的部署包

从 GitHub 下载本仓库分支里的文件：

```text
trustgraph-demo-kit/artifacts/deploy-openai-deepseek-compatible.zip
```

假设你把它下载到了本地 `Downloads` 目录：

```bash
mkdir -p ~/trustgraph-run
cd ~/trustgraph-run
unzip ~/Downloads/deploy-openai-deepseek-compatible.zip
```

解压后应该能看到：

```text
docker-compose.yaml
trustgraph/config.json
launch/
garage/
grafana/
loki/
prometheus/
```

> 如果你想重新生成不同配置的部署包，不要在受限网络的本地运行 `npx`。直接告诉我你要改哪些选项，我可以继续在云端生成新的 zip 并上传到 GitHub。

### 2. 设置 DeepSeek 和 TrustGraph 环境变量

在 `~/trustgraph-run` 目录里设置：

```bash
export IAM_BOOTSTRAP_TOKEN="tg_your-local-admin-token"
export TRUSTGRAPH_TOKEN="${IAM_BOOTSTRAP_TOKEN}"
export GF_SECURITY_ADMIN_PASSWORD="your-grafana-password"

export OPENAI_TOKEN="你的 DeepSeek API Key"
export OPENAI_BASE_URL="https://api.deepseek.com/v1"
```

注意：

- `IAM_BOOTSTRAP_TOKEN` 必须以 `tg_` 开头。
- `OPENAI_TOKEN` 填 DeepSeek API key。
- 不要把真实 key 提交到 GitHub。
- 如果你想写入本地 `.env`，请只保存在本机，不要上传。

### 3. 启动服务

在 `~/trustgraph-run` 目录执行：

```bash
docker compose -f docker-compose.yaml up -d
```

如果你使用的是旧版 Docker Compose，也可能是：

```bash
docker-compose -f docker-compose.yaml up -d
```

启动后需要等待一段时间，Cassandra、Pulsar、Qdrant、Garage、TrustGraph 服务都需要初始化。

### 4. 安装 TrustGraph CLI 并健康检查

官方教程会用 CLI 来检查系统和做 demo。建议单独建 Python venv：

```bash
cd ~/trustgraph-run
python3 -m venv env
. env/bin/activate
pip install trustgraph-cli
```

如果你的网络限制导致 `pip install trustgraph-cli` 也无法运行，可以先跳过 CLI：

- 直接进入下面的 Workbench UI。
- 用 UI 上传/提交文档。
- 用 UI 里的 Graph RAG Query、Document Ingestion、Graph Explorer、Ontology Workbench 体验功能。

如果你希望完全离线使用 CLI，可以让我继续帮你生成一个 `trustgraph-cli` 的离线 wheel 包集合并上传到 GitHub。

然后确认当前 shell 里还有这些环境变量：

```bash
export TRUSTGRAPH_TOKEN="${IAM_BOOTSTRAP_TOKEN}"
export TRUSTGRAPH_URL="http://localhost:8088/"
export TRUSTGRAPH_WORKSPACE="default"
```

运行健康检查：

```bash
tg-verify-system-status
```

如果健康检查还没通过，先等一会儿再重试。常见原因是 Cassandra/Pulsar 还没完成启动。

### 5. 打开 Workbench UI

浏览器打开：

```text
http://localhost:8888
```

登录方式：

1. 选择 `API Key`。
2. 填入你设置的 `IAM_BOOTSTRAP_TOKEN`，例如 `tg_your-local-admin-token`。
3. 点击连接。

Grafana 监控地址：

```text
http://localhost:3000
```

账号：

```text
admin
```

密码是你设置的：

```text
GF_SECURITY_ADMIN_PASSWORD
```

### 6. 加载样本文档

```bash
tg-load-sample-documents \
  --url "http://localhost:8088/" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "default"
```

样本文档在 TrustGraph CLI 包内，包括：

- West Country recipes
- Belgian beer
- Pre-modern European trade routes
- History of pets
- 19th century American coastal fortifications

加载完成后，进入 Workbench：

1. 打开 `Document Ingestion`。
2. 选择样本文档。
3. 点击 `Submit for Processing`。
4. Flow 选择 `default`。
5. Collection 选择 `default`。
6. 等待处理完成。

### 7. 重点观察 ontology / graph

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

### 8. RAG 查询

Document RAG：

```bash
tg-invoke-document-rag \
  --url "http://localhost:8088/" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "default" \
  --flow-id "default" \
  --collection "default" \
  --explainable \
  --question "In the sample documents, what are the most important entities and themes that should become ontology classes or properties?"
```

Graph RAG：

```bash
tg-invoke-graph-rag \
  --url "http://localhost:8088/" \
  --token "${TRUSTGRAPH_TOKEN}" \
  --workspace "default" \
  --flow-id "default" \
  --collection "default" \
  --explainable \
  --question "Using the knowledge graph, explain relationships between places, organizations, products, and historical processes in the sample documents. Highlight which relationships look ontology-worthy."
```

Ontology 相关问题建议：

```text
这些样本文档中有哪些核心实体类型？
Belgian beer 文档里，修道院、酵母、发酵方式之间有什么关系？
Pre-modern European trade routes 中，城市、商品、贸易路线之间是什么关系？
哪些概念可以被抽象成 ontology class，哪些更适合作为 instance？
```

### 9. 停止服务

如果只是暂停保留数据：

```bash
docker compose -f docker-compose.yaml stop
```

如果要彻底清理容器和数据卷：

```bash
docker compose -f docker-compose.yaml down -v -t 0
```

## 可选：本仓库脚本怎么用

`trustgraph-demo-kit/scripts/` 里的脚本主要是把上面的命令封装起来，适合你把整个仓库 clone
到本地后使用。

由于你本地网络受限，通常不要运行：

```bash
trustgraph-demo-kit/scripts/generate-deploy.sh
```

这个脚本内部会调用 `npx @trustgraph/config`。

你可以使用的脚本包括：

```bash
trustgraph-demo-kit/scripts/start.sh
trustgraph-demo-kit/scripts/verify.sh
trustgraph-demo-kit/scripts/load-samples.sh
trustgraph-demo-kit/scripts/query-document-rag.sh
trustgraph-demo-kit/scripts/query-graph-rag.sh
trustgraph-demo-kit/scripts/stop.sh
```

但最稳妥的方式仍然是直接照本 README 上面的手动命令执行。

## 阶段记录

- `notes/stage-1-demo-kit.md`：第 1 阶段，demo kit 与运行方案。
- `artifacts/stage-2-cloud-run.md`：第 2 阶段，官方部署包生成与云端运行尝试。
- `notes/ontology-learning-path.md`：ontology/RAG 学习路线。
- `notes/source-map.md`：TrustGraph 源码结构与重点文件。
- `notes/ontology-rag-source-deep-dive.md`：ontology 抽取、OntoRAG 查询、Graph RAG、Document RAG 源码深读。
- `artifacts/`：后续云端实跑日志、部署包摘要、截图说明等。

## 后续阶段计划

1. 第 1 阶段：完成本 demo kit，提交到 GitHub。
2. 第 2 阶段：尝试在云端安装容器环境、生成部署包并实跑；结果无论成功失败都写入 `artifacts/`。
3. 第 3 阶段：结合源码补充 ontology、Graph RAG、Document RAG 的学习笔记。

