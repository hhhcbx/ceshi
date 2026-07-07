# Stage 2: Cloud Deployment Attempt

## Result

The official TrustGraph deployment package was generated successfully, but the
complete TrustGraph stack could not be started in this Cursor cloud container.

Generated files committed in this directory:

- `deploy-openai-deepseek-compatible.zip`
- `INSTALLATION.generated.md`
- `deploy-zip-contents.txt`

## Generated configuration

Selections used in `npx @trustgraph/config`:

- TrustGraph version: 2.6 recommended by the configurator.
- Platform: Docker Compose.
- Pub/sub: Apache Pulsar.
- Graph store: Apache Cassandra.
- Vector database: Qdrant.
- Row data store: Apache Cassandra.
- Object store: Garage.
- LLM provider: OpenAI-compatible.
- Intended DeepSeek base URL: `https://api.deepseek.com/v1`.
- Maximum output tokens: 4096.
- OCR: disabled for first run.
- Embeddings engine: default FastEmbed.
- MCP server: enabled.

The ZIP contains:

- `docker-compose.yaml`
- `trustgraph/config.json`
- `launch/*/launch.yaml`
- Grafana dashboards/provisioning
- Prometheus/Loki/Garage configuration

## Cloud environment checks

Initially available:

- Python 3.12.
- Node.js/npm.
- 15GB RAM.
- 4 CPU cores.
- No Docker.
- No Podman.

Installed during this attempt:

- `podman`
- `podman-compose`
- `kmod`

Podman installed successfully and `podman info` worked in rootless mode.

## Failure reason

The compose stack could create containers, but container startup failed because
rootless Podman could not create the network namespace:

```text
failed to mount runtime directory for rootless netns: no such file or directory
```

A minimal container test then exposed the lower-level cause:

```text
/usr/bin/slirp4netns failed: open("/dev/net/tun"): No such file or directory
```

Creating `/dev/net/tun` was possible, but the kernel did not provide a working
tun device:

```text
open("/dev/net/tun"): No such device
```

Loading the module was not possible in this container:

```text
modprobe: FATAL: Module tun not found in directory /lib/modules/6.12.58+
could not open /proc/modules: No such file or directory
```

Conclusion: this cloud container cannot run rootless Podman networking for the
multi-container TrustGraph compose stack.

## What did work

This minimal test worked with host networking:

```bash
podman run --rm --network host docker.io/library/alpine:3.20 echo ok
```

However, TrustGraph compose depends on service DNS names and network aliases
between containers, so switching the whole stack to host networking is not a
safe drop-in fix.

## How to use the generated package locally

1. Download `deploy-openai-deepseek-compatible.zip`.
2. Copy `.env.example` to `.env`.
3. Fill:

```bash
OPENAI_TOKEN=your_deepseek_api_key
OPENAI_BASE_URL=https://api.deepseek.com/v1
IAM_BOOTSTRAP_TOKEN=tg_your_local_admin_token
TRUSTGRAPH_TOKEN=tg_your_local_admin_token
GF_SECURITY_ADMIN_PASSWORD=your_local_password
```

4. Unzip:

```bash
mkdir -p trustgraph-run
cd trustgraph-run
unzip ../deploy-openai-deepseek-compatible.zip
```

5. Start with Docker Compose:

```bash
docker compose -f docker-compose.yaml up -d
```

6. Install CLI and verify:

```bash
python3 -m venv env
. env/bin/activate
pip install trustgraph-cli
export TRUSTGRAPH_TOKEN="${IAM_BOOTSTRAP_TOKEN}"
tg-verify-system-status
```

7. Continue with the scripts in `trustgraph-demo-kit/scripts/`.

## Cleanup performed

The failed cloud containers and TrustGraph project volumes were removed after
the test. Pulled images may remain in the cloud Podman image cache.

