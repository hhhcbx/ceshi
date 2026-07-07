# Stage 1: Demo Kit

## 目标

第 1 阶段先不依赖本机能否启动完整容器环境，而是把 TrustGraph 的可复现运行方案沉淀到仓库里。

用户重点关注：

1. Ontology 相关内容。
2. 完整 RAG 体验。
3. LLM 后端使用 DeepSeek，按 OpenAI-compatible 配置预留。
4. 每个阶段完成后提交到 GitHub。

## 本阶段交付

- `README.zh-CN.md`
  - 中文入口文档。
  - 解释 ontology 与 Document RAG / Graph RAG 的关系。
  - 说明 DeepSeek 配置方式。
  - 给出 UI 与 CLI 演示路线。
- `.env.example`
  - 预留 `OPENAI_TOKEN`。
  - 默认 `OPENAI_BASE_URL=https://api.deepseek.com/v1`。
- `scripts/`
  - `generate-deploy.sh`
  - `start.sh`
  - `stop.sh`
  - `verify.sh`
  - `load-samples.sh`
  - `query-document-rag.sh`
  - `query-graph-rag.sh`
- `notes/`
  - 本阶段记录。
  - ontology 学习路线。
  - TrustGraph 源码结构索引。

## 当前云端机器状态

已确认：

- Python 3.12 可用。
- Node.js/npm 可用。
- 内存约 15GB。
- CPU 4 核。
- Docker/Docker Compose 当前不可用。

影响：

- 可以生成文档、脚本、源码学习材料。
- 不能直接按官方 Docker Compose 教程启动完整 TrustGraph，除非后续成功安装 Docker/Podman 并能运行容器。

## 下一阶段

第 2 阶段尝试生成官方部署包，并继续评估云端容器运行可行性。无论成功失败，都把命令、日志和结论写入 `artifacts/` 后提交。

