# Interactive gateway model discovery proof

PR https://github.com/BerriAI/litellm/pull/48205

The screenshots are unmodified captures of Claude Code 2.1.310 running interactively in xfce4-terminal on a virtual X display. No `claude -p` or simulated terminal UI was used

Before proxy commit 082064569082761bbb8ce1dc1b1be2fb2a145b94, `/model` showed only built-in fallback entries. The client's real `GET /claude_code_gateway/v1/models?limit=1000` received 404. After proxy commit c45d22f59da049ea79b77351ea726052ef712386, the same request received 200 and `/model` offered Gateway Demo and Gateway Second. Selecting Gateway Demo and submitting a prompt produced the streamed GATEWAY_OK response

## What is real and what is mocked

The Claude Code binary, interactive gateway login UI, browser approval, real proxy HTTP routing, gateway model-list handler, credential checking against the local master key, model catalog, and Anthropic message adapter all ran normally

A local mock OAuth service handled authorization-server metadata, device authorization, browser approval, and token exchange. It issued the disposable local proxy master key as a test bearer. This deliberately does not validate LiteLLM's enterprise SSO, its device-token minting, or end-user model restrictions. The mock auth front forwards every other request to LiteLLM unchanged, including the discovery and prompt routes under test

The inference provider was also a local mock serving Anthropic JSON and SSE replies. No real provider credential, billable model request, production identity, or native Claude Desktop session was used. An auxiliary CLI request for an unconfigured built-in Haiku model received 400; the selected gateway model's streaming requests both succeeded with 200

## Reproduce

Use the same local key in all three services. Generate it locally and do not publish it

```bash
export LITELLM_MASTER_KEY="$(python -c 'import secrets; print("sk-"+secrets.token_hex(32))')"
```

With aiohttp available, start the mock provider on 127.0.0.1:4010 and mock OAuth front on 127.0.0.1:4002 in separate terminals

```bash
python mock_provider.py
python mock_auth_front.py
```

Start either the before or after LiteLLM source checkout on port 4000 with the supplied config. Both use identical settings

```bash
PYTHONPATH=. LITELLM_LOCAL_MODEL_COST_MAP=True python litellm/proxy/proxy_cli.py --config /absolute/path/to/config.yaml --port 4000
```

Install the pinned Claude Code release in a disposable directory

```bash
npm install --prefix /tmp/gateway-qa @anthropic-ai/claude-code@2.1.310
```

Create a disposable user configuration directory, copy claude-settings.json to its settings.json, and run the interactive client. Do not set ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN in this client shell

```bash
CLAUDE_CONFIG_DIR=/tmp/gateway-user CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY=1 CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 /tmp/gateway-qa/node_modules/.bin/claude
```

Run `/login`, connect to http://localhost:4002/claude_code_gateway, trust the local gateway, and open http://localhost:4002/verify in a browser. Click Approve local test sign-in and return to the client. Restart the client to load the catalog, then open `/model`

Capture the before picker. Stop the old proxy, start the fixed proxy on the same port with the same config, restart the same signed-in client, and capture `/model` again. Select Gateway Demo, then send `Reply with GATEWAY_OK to confirm the local mock provider is reachable.`

The JSONL files are sanitized wire records from the run. They contain no request headers, access tokens, device codes, or real credentials
