<div align="center">
<a href="https://swipies.ai/">
<img src="web/src/assets/logo-with-text.png" width="520" alt="Swipies AI logo">
</a>
</div>

<p align="center">
  <a href="./README.md"><img alt="README in English" src="https://img.shields.io/badge/English-DBEDFA"></a>
  <a href="./README_zh.md"><img alt="简体中文版自述文件" src="https://img.shields.io/badge/简体中文-DFE0E5"></a>
  <a href="./README_tzh.md"><img alt="繁體版中文自述文件" src="https://img.shields.io/badge/繁體中文-DFE0E5"></a>
  <a href="./README_ja.md"><img alt="日本語のREADME" src="https://img.shields.io/badge/日本語-DFE0E5"></a>
  <a href="./README_ko.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-DFE0E5"></a>
  <a href="./README_id.md"><img alt="Bahasa Indonesia" src="https://img.shields.io/badge/Bahasa Indonesia-DFE0E5"></a>
  <a href="./README_pt_br.md"><img alt="Português(Brasil)" src="https://img.shields.io/badge/Português(Brasil)-DFE0E5"></a>
</p>

<p align="center">
    <a href="https://x.com/intent/follow?screen_name=swipiesai" target="_blank">
        <img src="https://img.shields.io/twitter/follow/swipiesai?logo=X&color=%20%23f5f5f5" alt="follow on X(Twitter)">
    </a>
    <a href="https://demo.swipies.ai" target="_blank">
        <img alt="Static Badge" src="https://img.shields.io/badge/Online-Demo-4e6b99">
    </a>
    <a href="https://hub.docker.com/r/swipies/ragflow" target="_blank">
        <img src="https://img.shields.io/docker/pulls/swipies/ragflow?label=Docker%20Pulls&color=0db7ed&logo=docker&logoColor=white&style=flat-square" alt="docker pull swipies/ragflow:latest">
    </a>
    <a href="https://github.com/swipies/ragflow/releases/latest">
        <img src="https://img.shields.io/github/v/release/swipies/ragflow?color=blue&label=Latest%20Release" alt="Latest Release">
    </a>
    <a href="https://github.com/swipies/ragflow/blob/main/LICENSE">
        <img height="21" src="https://img.shields.io/badge/License-Apache--2.0-ffffff?labelColor=d4eaf7&color=2e6cc4" alt="license">
    </a>
</p>

<h4 align="center">
  <a href="https://swipies.ai/docs/">Documentation</a> |
  <a href="https://github.com/swipies/ragflow/issues">Roadmap</a> |
  <a href="https://twitter.com/swipiesai">Twitter</a> |
  <a href="https://discord.gg/swipiesai">Discord</a> |
  <a href="https://demo.swipies.ai">Demo</a>
</h4>

#

<div align="center">
<a href="https://trendshift.io/repositories/swipies" target="_blank"><img src="https://trendshift.io/api/badge/repositories/swipies" alt="swipies%2Fragflow | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</div>

<details open>
<summary><b>📕 Table of Contents</b></summary>

- 💡 [What is Swipies AI?](#-what-is-swipies-ai)
- 🎮 [Demo](#-demo)
- 📌 [Latest Updates](#-latest-updates)
- 🌟 [Key Features](#-key-features)
- 🔎 [System Architecture](#-system-architecture)
- 🎬 [Get Started](#-get-started)
- 🔧 [Configurations](#-configurations)
- 🔧 [Build a docker image without embedding models](#-build-a-docker-image-without-embedding-models)
- 🔧 [Build a docker image including embedding models](#-build-a-docker-image-including-embedding-models)
- 🔨 [Launch service from source for development](#-launch-service-from-source-for-development)
- 📚 [Documentation](#-documentation)
- 📜 [Roadmap](#-roadmap)
- 🏄 [Community](#-community)
- 🙌 [Contributing](#-contributing)

</details>

## 💡 What is Swipies AI?

**Swipies AI** is our customized RAG (Retrieval-Augmented Generation) engine, built upon the powerful foundation of [RAGFlow](https://ragflow.io/) by InfiniFlow. We've taken the excellent open-source RAGFlow framework and adapted it specifically for our project's needs and requirements.

### 🏗️ **Built on RAGFlow Foundation**

This project is based on [RAGFlow](https://github.com/infiniflow/ragflow), an open-source RAG engine based on deep document understanding. We've customized and enhanced it to create **Swipies AI** - a tailored solution that combines:

- **Deep document understanding** capabilities from RAGFlow
- **Streamlined RAG workflow** optimized for our specific use cases
- **Custom integrations** and modifications for our business requirements
- **Enhanced features** built on top of the solid RAGFlow foundation

### 🎯 **Our Customizations**

While maintaining the core strengths of RAGFlow, we've made specific adaptations including:
- Custom UI/UX tailored to our brand
- Specialized document processing workflows
- Integration with our specific data sources and APIs
- Optimized performance for our use cases
- Enhanced security and compliance features

## 🎮 Demo

Try our demo at [https://demo.swipies.ai](https://demo.swipies.ai).

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://raw.githubusercontent.com/swipies/ragflow-docs/refs/heads/image/image/chunking.gif" width="1200"/>
<img src="https://raw.githubusercontent.com/swipies/ragflow-docs/refs/heads/image/image/agentic-dark.gif" width="1200"/>
</div>

## 🔥 Latest Updates

- 2025-01-XX Customized RAGFlow for Swipies AI project
- 2025-01-XX Enhanced document processing workflows
- 2025-01-XX Integrated custom UI/UX components
- 2025-01-XX Optimized performance for our specific use cases
- 2025-01-XX Added specialized integrations and APIs

## 🎉 Stay Tuned

⭐️ Star our repository to stay up-to-date with exciting new features and improvements! Get instant notifications for new releases! 🌟

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/user-attachments/assets/18c9707e-b8aa-4caf-a154-037089c105ba" width="1200"/>
</div>

## 🌟 Key Features

### 🍭 **"Quality in, quality out"**

- [Deep document understanding](./deepdoc/README.md)-based knowledge extraction from unstructured data with complicated formats (inherited from RAGFlow)
- Finds "needle in a data haystack" of literally unlimited tokens
- **Custom enhancements** for our specific document types and use cases

### 🍱 **Template-based chunking**

- Intelligent and explainable chunking strategies
- Plenty of template options to choose from
- **Custom templates** optimized for our content types

### 🌱 **Grounded citations with reduced hallucinations**

- Visualization of text chunking to allow human intervention
- Quick view of the key references and traceable citations to support grounded answers
- **Enhanced citation tracking** for our specific requirements

### 🍔 **Compatibility with heterogeneous data sources**

- Supports Word, slides, excel, txt, images, scanned copies, structured data, web pages, and more
- **Custom data source integrations** for our specific needs

### 🛀 **Automated and effortless RAG workflow**

- Streamlined RAG orchestration catered to both personal and large businesses
- Configurable LLMs as well as embedding models
- Multiple recall paired with fused re-ranking
- Intuitive APIs for seamless integration with business
- **Custom workflow optimizations** for our use cases

## 🔎 System Architecture

<div align="center" style="margin-top:20px;margin-bottom:20px;">
<img src="https://github.com/swipies/ragflow/assets/12318111/d6ac5664-c237-4200-a7c2-a4a00691b485" width="1000"/>
</div>

*Architecture diagram showing our customized Swipies AI system built on RAGFlow foundation*

## 🎬 Get Started

### 📝 Prerequisites

- CPU >= 4 cores
- RAM >= 16 GB
- Disk >= 50 GB
- Docker >= 24.0.0 & Docker Compose >= v2.26.1
- [gVisor](https://gvisor.dev/docs/user_guide/install/): Required only if you intend to use the code executor (sandbox) feature

> [!TIP]
> If you have not installed Docker on your local machine (Windows, Mac, or Linux), see [Install Docker Engine](https://docs.docker.com/engine/install/).

### 🚀 Start up the server

1. Ensure `vm.max_map_count` >= 262144:

   > To check the value of `vm.max_map_count`:
   >
   > ```bash
   > $ sysctl vm.max_map_count
   > ```
   >
   > Reset `vm.max_map_count` to a value at least 262144 if it is not.
   >
   > ```bash
   > # In this case, we set it to 262144:
   > $ sudo sysctl -w vm.max_map_count=262144
   > ```
   >
   > This change will be reset after a system reboot. To ensure your change remains permanent, add or update the
   > `vm.max_map_count` value in **/etc/sysctl.conf** accordingly:
   >
   > ```bash
   > vm.max_map_count=262144
   > ```

2. Clone the repo:

   ```bash
   $ git clone https://github.com/swipies/ragflow.git
   ```

3. Start up the server using the pre-built Docker images:

> [!CAUTION]
> All Docker images are built for x86 platforms. We don't currently offer Docker images for ARM64.
> If you are on an ARM64 platform, follow [this guide](https://swipies.ai/docs/dev/build_docker_image) to build a Docker image compatible with your system.

   > The command below downloads the `latest-slim` edition of the Swipies AI Docker image. See the following table for descriptions of different image editions. To download a different edition, update the `RAGFLOW_IMAGE` variable accordingly in **docker/.env** before using `docker compose` to start the server.

   ```bash
   $ cd ragflow/docker
   # Use CPU for embedding and DeepDoc tasks:
   $ docker compose -f docker-compose.yml up -d

   # To use GPU to accelerate embedding and DeepDoc tasks:
   # docker compose -f docker-compose-gpu.yml up -d
   ```

   | Swipies AI image tag | Image size (GB) | Has embedding models? | Stable?                  |
   |---------------------|-----------------|----------------------|--------------------------|
   | latest              | &approx;9       | :heavy_check_mark:    | Stable release           |
   | latest-slim         | &approx;2       | ❌                   | Stable release            |
   | nightly             | &approx;9       | :heavy_check_mark:    | _Unstable_ nightly build |
   | nightly-slim        | &approx;2       | ❌                   | _Unstable_ nightly build  |

4. Check the server status after having the server up and running:

   ```bash
   $ docker logs -f ragflow-server
   ```

   _The following output confirms a successful launch of the system:_

   ```bash

         ____   ___    ______ ______ __
        / __ \ /   |  / ____// ____// /____  _      __
       / /_/ // /| | / / __ / /_   / // __ \| | /| / /
      / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ /
     /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/

    * Running on all addresses (0.0.0.0)
   ```

   > If you skip this confirmation step and directly log in to Swipies AI, your browser may prompt a `network anormal`
   > error because, at that moment, your Swipies AI may not be fully initialized.

5. In your web browser, enter the IP address of your server and log in to Swipies AI.
   > With the default settings, you only need to enter `http://IP_OF_YOUR_MACHINE` (**sans** port number) as the default
   > HTTP serving port `80` can be omitted when using the default configurations.
6. In [service_conf.yaml.template](./docker/service_conf.yaml.template), select the desired LLM factory in `user_default_llm` and update
   the `API_KEY` field with the corresponding API key.

   > See [llm_api_key_setup](https://swipies.ai/docs/dev/llm_api_key_setup) for more information.

   _The show is on!_

## 🔧 Configurations

When it comes to system configurations, you will need to manage the following files:

- [.env](./docker/.env): Keeps the fundamental setups for the system, such as `SVR_HTTP_PORT`, `MYSQL_PASSWORD`, and
  `MINIO_PASSWORD`.
- [service_conf.yaml.template](./docker/service_conf.yaml.template): Configures the back-end services. The environment variables in this file will be automatically populated when the Docker container starts. Any environment variables set within the Docker container will be available for use, allowing you to customize service behavior based on the deployment environment.
- [docker-compose.yml](./docker/docker-compose.yml): The system relies on [docker-compose.yml](./docker/docker-compose.yml) to start up.

> The [./docker/README](./docker/README.md) file provides a detailed description of the environment settings and service
> configurations which can be used as `${ENV_VARS}` in the [service_conf.yaml.template](./docker/service_conf.yaml.template) file.

To update the default HTTP serving port (80), go to [docker-compose.yml](./docker/docker-compose.yml) and change `80:80`
to `<YOUR_SERVING_PORT>:80`.

Updates to the above configurations require a reboot of all containers to take effect:

> ```bash
> $ docker compose -f docker-compose.yml up -d
> ```

### Switch doc engine from Elasticsearch to Infinity

Swipies AI uses Elasticsearch by default for storing full text and vectors. To switch to [Infinity](https://github.com/infiniflow/infinity/), follow these steps:

1. Stop all running containers:

   ```bash
   $ docker compose -f docker/docker-compose.yml down -v
   ```

> [!WARNING]
> `-v` will delete the docker container volumes, and the existing data will be cleared.

2. Set `DOC_ENGINE` in **docker/.env** to `infinity`.

3. Start the containers:

   ```bash
   $ docker compose -f docker-compose.yml up -d
   ```

> [!WARNING]
> Switching to Infinity on a Linux/arm64 machine is not yet officially supported.

## 🔧 Build a Docker image without embedding models

This image is approximately 2 GB in size and relies on external LLM and embedding services.

```bash
git clone https://github.com/swipies/ragflow.git
cd ragflow/
docker build --platform linux/amd64 --build-arg LIGHTEN=1 -f Dockerfile -t swipies/ragflow:nightly-slim .
```

## 🔧 Build a Docker image including embedding models

This image is approximately 9 GB in size. As it includes embedding models, it relies on external LLM services only.

```bash
git clone https://github.com/swipies/ragflow.git
cd ragflow/
docker build --platform linux/amd64 -f Dockerfile -t swipies/ragflow:nightly .
```

## 🔨 Launch service from source for development

1. Install uv, or skip this step if it is already installed:

   ```bash
   pipx install uv pre-commit
   ```

2. Clone the source code and install Python dependencies:

   ```bash
   git clone https://github.com/swipies/ragflow.git
   cd ragflow/
   uv sync --python 3.10 --all-extras # install Swipies AI dependent python modules
   uv run download_deps.py
   pre-commit install
   ```

3. Launch the dependent services (MinIO, Elasticsearch, Redis, and MySQL) using Docker Compose:

   ```bash
   docker compose -f docker/docker-compose-base.yml up -d
   ```

   Add the following line to `/etc/hosts` to resolve all hosts specified in **docker/.env** to `127.0.0.1`:

   ```
   127.0.0.1       es01 infinity mysql minio redis sandbox-executor-manager
   ```

4. If you cannot access HuggingFace, set the `HF_ENDPOINT` environment variable to use a mirror site:

   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

5. If your operating system does not have jemalloc, please install it as follows:

   ```bash
   # ubuntu
   sudo apt-get install libjemalloc-dev
   # centos
   sudo yum install jemalloc
   ```
   
6. Launch backend service:

   ```bash
   source .venv/bin/activate
   export PYTHONPATH=$(pwd)
   bash docker/launch_backend_service.sh
   ```

7. Install frontend dependencies:

   ```bash
   cd web
   npm install
   ```

8. Launch frontend service:

   ```bash
   npm run dev
   ```

   _The following output confirms a successful launch of the system:_

   ![](https://github.com/user-attachments/assets/0daf462c-a24d-4496-a66f-92533534e187)

9. Stop Swipies AI front-end and back-end service after development is complete:

   ```bash
   pkill -f "ragflow_server.py|task_executor.py"
   ```


## 📚 Documentation

- [Quickstart](https://swipies.ai/docs/dev/)
- [Configuration](https://swipies.ai/docs/dev/configurations)
- [Release notes](https://swipies.ai/docs/dev/release_notes)
- [User guides](https://swipies.ai/docs/dev/category/guides)
- [Developer guides](https://swipies.ai/docs/dev/category/developers)
- [References](https://swipies.ai/docs/dev/category/references)
- [FAQs](https://swipies.ai/docs/dev/faq)

## 📜 Roadmap

See the [Swipies AI Roadmap 2025](https://github.com/swipies/ragflow/issues)

## 🏄 Community

- [Discord](https://discord.gg/swipiesai)
- [Twitter](https://twitter.com/swipiesai)
- [GitHub Discussions](https://github.com/orgs/swipies/discussions)

## 🙌 Contributing

Swipies AI flourishes via open-source collaboration. In this spirit, we embrace diverse contributions from the community.
If you would like to be a part, review our [Contribution Guidelines](https://swipies.ai/docs/dev/contributing) first.

## 🙏 Acknowledgments

We would like to express our gratitude to the [RAGFlow](https://github.com/infiniflow/ragflow) team at InfiniFlow for creating such an excellent open-source RAG engine. Swipies AI is built upon their solid foundation, and we appreciate their contribution to the open-source community.

---

<div align="center">
<p><strong>Built with ❤️ by the Swipies AI team</strong></p>
<p><em>Powered by RAGFlow • Enhanced for Swipies AI</em></p>
</div>