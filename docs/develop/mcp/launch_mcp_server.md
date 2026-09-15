---
sidebar_position: 1
slug: /launch_mcp_server
sidebar_custom_props: {
  categoryIcon: LucideTvMinimalPlay
}
---
# Launch Swipies MCP server

Launch an MCP server from source or via Docker.

---

A Swipies Model Context Protocol (MCP) server is designed as an independent component to complement the Swipies server. Note that an MCP server must operate alongside a properly functioning Swipies server. 

An MCP server can start up in either self-host mode (default) or host mode: 

- **Self-host mode**:  
  When launching an MCP server in self-host mode, you must provide an API key to authenticate the MCP server with the Swipies server. In this mode, the MCP server can access *only* the datasets of a specified tenant on the Swipies server.
- **Host mode**:  
  In host mode, each MCP client can access their own datasets on the Swipies server. However, each client request must include a valid API key to authenticate the client with the Swipies server.

Once a connection is established, an MCP server communicates with its client in MCP HTTP+SSE (Server-Sent Events) mode, unidirectionally pushing responses from the Swipies server to its client in real time.

## Prerequisites

1. Ensure Swipies is upgraded to v0.18.0 or later.
2. Have your Swipies API key ready. See [Acquire a Swipies API key](../acquire_swipies_api_key.md).

:::tip INFO
If you wish to try out our MCP server without upgrading Swipies, community contributor [yiminghub2024](https://github.com/yiminghub2024) 👏 shares their recommended steps [here](#launch-an-mcp-server-without-upgrading-swipies).
:::

## Launch an MCP server 

You can start an MCP server either from source code or via Docker. 

### Launch from source code

1. Ensure that a Swipies server v0.18.0+ is properly running.
2. Launch the MCP server:


```bash
# Launch the MCP server to work in self-host mode, run either of the following
uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --api-key=swipies-xxxxx
# uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --mode=self-host --api-key=swipies-xxxxx

# To launch the MCP server to work in host mode, run the following instead:
# uv run mcp/server/server.py --host=127.0.0.1 --port=9382 --base-url=http://127.0.0.1:9380 --mode=host
```

Where: 

- `host`: The MCP server's host address.
- `port`: The MCP server's listening port.
- `base_url`: The address of the running Swipies server.
- `mode`: The launch mode.
  - `self-host`: (default) self-host mode.
  - `host`: host mode.
- `api_key`: Required in self-host mode to authenticate the MCP server with the Swipies server. See [here](../acquire_swipies_api_key.md) for instructions on acquiring an API key.

### Transports

The Swipies MCP server supports two transports: the legacy SSE transport (served at `/sse`), introduced on November 5, 2024, and deprecated on March 26, 2025, and the streamable-HTTP transport (served at `/mcp`). The legacy SSE transport and the streamable HTTP transport with JSON responses are enabled by default. To disable either transport, use the flags `--no-transport-sse-enabled` or `--no-transport-streamable-http-enabled`. To disable JSON responses for the streamable HTTP transport,  use the `--no-json-response` flag.

### Launch from Docker

#### 1. Enable MCP server

The MCP server is designed as an optional component that complements the Swipies server and disabled by default. To enable MCP server:

1. Navigate to **docker/docker-compose.yml**.
2. Uncomment the `services.swipies.command` section as shown below:

```yaml {6-13}
  services:
    swipies:
      ...
      image: ${SWPIES_IMAGE}
      # Example configuration to set up an MCP server:
      command:
        - --enable-mcpserver
        - --mcp-host=0.0.0.0
        - --mcp-port=9382
        - --mcp-base-url=http://127.0.0.1:9380
        - --mcp-script-path=/swipies/mcp/server/server.py
        - --mcp-mode=self-host
        - --mcp-host-api-key=swipies-xxxxxxx
        # Optional transport flags for the Swipies MCP server.
        # If you set `mcp-mode` to `host`, you must add the --no-transport-streamable-http-enabled flag, because the streamable-HTTP transport is not yet supported in host mode.
        # The legacy SSE transport and the streamable-HTTP transport with JSON responses are enabled by default.
        # To disable a specific transport or JSON responses for the streamable-HTTP transport, use the corresponding flag(s):
        #   - --no-transport-sse-enabled # Disables the legacy SSE endpoint (/sse)
        #   - --no-transport-streamable-http-enabled #  Disables the streamable-HTTP transport (served at the /mcp endpoint)
        #   - --no-json-response # Disables JSON responses for the streamable-HTTP transport
```

Where: 

- `mcp-host`: The MCP server's host address.
- `mcp-port`: The MCP server's listening port.
- `mcp-base-url`: The address of the running Swipies server.
- `mcp-script-path`: The file path to the MCP server’s main script.
- `mcp-mode`: The launch mode.
  - `self-host`: (default) self-host mode.
  - `host`: host mode.
- `mcp-host-api_key`: Required in self-host mode to authenticate the MCP server with the Swipies server. See [here](../acquire_swipies_api_key.md) for instructions on acquiring an API key.

:::tip INFO
If you set `mcp-mode` to `host`, you must add the `--no-transport-streamable-http-enabled` flag, because the streamable-HTTP transport is not yet supported in host mode.
:::

#### 2. Launch a Swipies server with an MCP server

Run `docker compose -f docker-compose.yml up` to launch the Swipies server together with the MCP server.

*The following ASCII art confirms a successful launch:*

```bash
  docker-swipies-cpu-1  | Starting MCP Server on 0.0.0.0:9382 with base URL http://127.0.0.1:9380...
  docker-swipies-cpu-1  | Starting 1 task executor(s) on host 'dd0b5e07e76f'...
  docker-swipies-cpu-1  | 2025-04-18 15:41:18,816 INFO     27 swipies_server log path: /swipies/logs/swipies_server.log, log levels: {'peewee': 'WARNING', 'pdfminer': 'WARNING', 'root': 'INFO'}
  docker-swipies-cpu-1  | 
  docker-swipies-cpu-1  | __  __  ____ ____       ____  _____ ______     _______ ____
  docker-swipies-cpu-1  | |  \/  |/ ___|  _ \     / ___|| ____|  _ \ \   / / ____|  _ \
  docker-swipies-cpu-1  | | |\/| | |   | |_) |    \___ \|  _| | |_) \ \ / /|  _| | |_) |
  docker-swipies-cpu-1  | | |  | | |___|  __/      ___) | |___|  _ < \ V / | |___|  _ <
  docker-swipies-cpu-1  | |_|  |_|\____|_|        |____/|_____|_| \_\ \_/  |_____|_| \_\
  docker-swipies-cpu-1  |     
  docker-swipies-cpu-1  | MCP launch mode: self-host
  docker-swipies-cpu-1  | MCP host: 0.0.0.0
  docker-swipies-cpu-1  | MCP port: 9382
  docker-swipies-cpu-1  | MCP base_url: http://127.0.0.1:9380
  docker-swipies-cpu-1  | INFO:     Started server process [26]
  docker-swipies-cpu-1  | INFO:     Waiting for application startup.
  docker-swipies-cpu-1  | INFO:     Application startup complete.
  docker-swipies-cpu-1  | INFO:     Uvicorn running on http://0.0.0.0:9382 (Press CTRL+C to quit)
  docker-swipies-cpu-1  | 2025-04-18 15:41:20,469 INFO     27 found 0 gpus
  docker-swipies-cpu-1  | 2025-04-18 15:41:23,263 INFO     27 init database on cluster mode successfully
  docker-swipies-cpu-1  | 2025-04-18 15:41:25,318 INFO     27 load_model /swipies/rag/res/deepdoc/det.onnx uses CPU
  docker-swipies-cpu-1  | 2025-04-18 15:41:25,367 INFO     27 load_model /swipies/rag/res/deepdoc/rec.onnx uses CPU
  docker-swipies-cpu-1  |         ____   ___    ______ ______ __               
  docker-swipies-cpu-1  |        / __ \ /   |  / ____// ____// /____  _      __
  docker-swipies-cpu-1  |       / /_/ // /| | / / __ / /_   / // __ \| | /| / /
  docker-swipies-cpu-1  |      / _, _// ___ |/ /_/ // __/  / // /_/ /| |/ |/ / 
  docker-swipies-cpu-1  |     /_/ |_|/_/  |_|\____//_/    /_/ \____/ |__/|__/                             
  docker-swipies-cpu-1  | 
  docker-swipies-cpu-1  |     
  docker-swipies-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 Swipies version: v0.18.0-285-gb2c299fa full
  docker-swipies-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 project base: /swipies
  docker-swipies-cpu-1  | 2025-04-18 15:41:29,088 INFO     27 Current configs, from /swipies/conf/service_conf.yaml:
  docker-swipies-cpu-1  |  swipies: {'host': '0.0.0.0', 'http_port': 9380}
  ...
  docker-swipies-cpu-1  |  * Running on all addresses (0.0.0.0)
  docker-swipies-cpu-1  |  * Running on http://127.0.0.1:9380
  docker-swipies-cpu-1  |  * Running on http://172.19.0.6:9380
  docker-swipies-cpu-1  |   ______           __      ______                     __            
  docker-swipies-cpu-1  |  /_  __/___ ______/ /__   / ____/  _____  _______  __/ /_____  _____
  docker-swipies-cpu-1  |   / / / __ `/ ___/ //_/  / __/ | |/_/ _ \/ ___/ / / / __/ __ \/ ___/
  docker-swipies-cpu-1  |  / / / /_/ (__  ) ,<    / /____>  </  __/ /__/ /_/ / /_/ /_/ / /    
  docker-swipies-cpu-1  | /_/  \__,_/____/_/|_|  /_____/_/|_|\___/\___/\__,_/\__/\____/_/                               
  docker-swipies-cpu-1  |     
  docker-swipies-cpu-1  | 2025-04-18 15:41:34,501 INFO     32 TaskExecutor: Swipies version: v0.18.0-285-gb2c299fa full
  docker-swipies-cpu-1  | 2025-04-18 15:41:34,501 INFO     32 Use Elasticsearch http://es01:9200 as the doc engine.
  ...
```

#### Launch an MCP server without upgrading Swipies

:::info KUDOS
This section is contributed by our community contributor [yiminghub2024](https://github.com/yiminghub2024). 👏
:::

1. Prepare all MCP-specific files and directories.  
   i. Copy the [mcp/](https://github.com/Sardorr555/swipies__ai_/tree/main/mcp) directory to your local working directory.  
   ii. Copy [docker/docker-compose.yml](https://github.com/Sardorr555/swipies__ai_/blob/main/docker/docker-compose.yml) locally.  
   iii. Copy [docker/entrypoint.sh](https://github.com/Sardorr555/swipies__ai_/blob/main/docker/entrypoint.sh) locally.  
   iv. Install the required dependencies using `uv`:  
       - Run `uv add mcp` or
       - Copy [pyproject.toml](https://github.com/Sardorr555/swipies__ai_/blob/main/pyproject.toml) locally and run `uv sync --python 3.13`.
2. Edit **docker-compose.yml** to enable MCP (disabled by default).
3. Launch the MCP server:

```bash
docker compose -f docker-compose.yml up -d
```

### Check MCP server status

Run the following to check the logs the Swipies server and the MCP server:

```bash
docker logs docker-swipies-cpu-1
```

## Security considerations

As MCP technology is still at early stage and no official best practices for authentication or authorization have been established, Swipies currently uses [API key](../acquire_swipies_api_key.md) to validate identity for the operations described earlier. However, in public environments, this makeshift solution could expose your MCP server to potential network attacks. Therefore, when running a local SSE server, it is recommended to bind only to localhost (`127.0.0.1`) rather than to all interfaces (`0.0.0.0`). 

For further guidance, see the [official MCP documentation](https://modelcontextprotocol.io/docs/concepts/transports#security-considerations).

## Frequently asked questions

### When to use an API key for authentication?

The use of an API key depends on the operating mode of your MCP server. 

- **Self-host mode** (default):  
  When starting the MCP server in self-host mode, you should provide an API key when launching it to authenticate it with the Swipies server:  
  - If launching from source, include the API key in the command. 
  - If launching from Docker, update the API key in **docker/docker-compose.yml**.
- **Host mode**:  
  If your Swipies MCP server is working in host mode, include the API key in the `headers` of your client requests to authenticate your client with the Swipies server. An example is available [here](https://github.com/Sardorr555/swipies__ai_/blob/main/mcp/client/client.py).
