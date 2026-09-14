# TME MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server for the [TME](https://www.tme.eu) electronic components API, built with [FastMCP](https://github.com/jlowin/fastmcp). Docker-first, designed for the [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/).

TME is a major European electronic components distributor based in Poland. Targets **TME API v2** (OAuth 2.0). Provides 14 tools: product search, details, pricing (with volume tiers), stock levels, datasheets, delivery time, and URL generation.

## Prerequisites

- **TME API credentials** -- Register at [developers.tme.eu](https://developers.tme.eu) (requires an active tme.eu customer account), create an application to get your **App Token** and **App Secret**. Applications created after May 14, 2026 only work with API v2, which is what this server uses.
- **Docker** (recommended) or Python 3.10+
- **Docker MCP Toolkit** -- included with [Docker Desktop](https://www.docker.com/products/docker-desktop/) (requires MCP Toolkit support)

## Project Structure

```
tme-mcp/
├── mcp_app.py           # Shared FastMCP instance
├── tme_mcp_server.py    # Main server -- all 14 tools
├── tme_auth.py          # OAuth 2.0 token handling + API request helper
├── Dockerfile           # Docker image with embedded metadata
├── pyproject.toml       # Project metadata
└── LICENSE              # MIT
```

## Quick Start -- Docker MCP Toolkit

The recommended way to run this server. The Docker MCP gateway manages the container lifecycle, injects secrets, and exposes tools to MCP clients like Claude Code or Claude Desktop.

### 1. Build the Docker image

```bash
git clone https://github.com/simon-77/tme-mcp.git
cd tme-mcp
docker build -t tme-mcp:latest .
```

### 2. Create a custom catalog

The gateway discovers servers through catalog files. Create one at `~/.docker/mcp/catalogs/custom.yaml` (or add to an existing one):

```yaml
version: 3
name: custom
displayName: Custom MCP Servers
registry:
  tme:
    description: TME electronic components -- search, pricing, stock, datasheets
    title: TME
    type: server
    image: tme-mcp:latest
    secrets:
      - name: tme.TME_APP_TOKEN
        env: TME_APP_TOKEN
      - name: tme.TME_APP_SECRET
        env: TME_APP_SECRET
    env:
      - name: TME_COUNTRY
        value: "PL"
      - name: TME_LANGUAGE
        value: "EN"
      - name: TME_CURRENCY
        value: "PLN"
    tools:
      - name: search_products
      - name: get_categories
      - name: search_parameters
      - name: get_manufacturers
      - name: get_products
      - name: get_parameters
      - name: get_product_files
      - name: get_similar_products
      - name: get_related_products
      - name: get_prices
      - name: get_stocks
      - name: get_prices_and_stocks
      - name: get_delivery_time
      - name: generate_tme_url
    prompts: 0
    resources: {}
```

Change the `env` values to match your locale (e.g., `AT`/`EN`/`EUR` for Austria).

### 3. Register the catalog and enable the server

```bash
docker mcp catalog import ~/.docker/mcp/catalogs/custom.yaml
docker mcp server enable tme
```

Re-run `catalog import` whenever you modify `custom.yaml`.

### 4. Set secrets

```bash
docker mcp secret set tme.TME_APP_TOKEN
docker mcp secret set tme.TME_APP_SECRET
```

You'll be prompted to enter each value. Secret names **must** be prefixed with the server name (`tme.`).

### 5. Connect an MCP client

```bash
docker mcp client connect claude-code
```

This adds the gateway to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "MCP_DOCKER": {
      "command": "docker",
      "args": ["mcp", "gateway", "run"],
      "type": "stdio"
    }
  }
}
```

When the MCP client starts, the gateway launches the `tme-mcp:latest` container, injects secrets as environment variables, and proxies tool calls.

### Rebuilding after changes

```bash
docker build -t tme-mcp:latest .
# Restart your MCP client to pick up the new image
```

No need to re-import the catalog or re-set secrets -- just rebuild and restart.

## Alternative: Docker standalone

Run the container directly without the MCP Toolkit. You manage secrets and lifecycle yourself.

```bash
docker build -t tme-mcp .

docker run --rm -i \
  -e TME_APP_TOKEN="your-token" \
  -e TME_APP_SECRET="your-secret" \
  -e TME_COUNTRY=AT \
  -e TME_CURRENCY=EUR \
  tme-mcp:latest
```

`.mcp.json` for MCP clients:

```json
{
  "mcpServers": {
    "tme": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "TME_APP_TOKEN",
        "-e", "TME_APP_SECRET",
        "-e", "TME_COUNTRY=AT",
        "-e", "TME_CURRENCY=EUR",
        "tme-mcp:latest"
      ]
    }
  }
}
```

When using `-e TME_APP_TOKEN` (without `=value`), Docker passes through the value from your shell. Make sure to `export` them first:

```bash
export TME_APP_TOKEN="your-token"
export TME_APP_SECRET="your-secret"
```

Locale env vars are optional -- defaults are `PL`/`EN`/`PLN` (see [Configuration](#configuration)).

## Alternative: Standalone (pip)

Run without Docker. Requires Python 3.10+.

```bash
git clone https://github.com/simon-77/tme-mcp.git
cd tme-mcp
pip install .

cat > .env <<EOF
TME_APP_TOKEN=your-token
TME_APP_SECRET=your-secret
TME_COUNTRY=AT
TME_LANGUAGE=EN
TME_CURRENCY=EUR
EOF

python tme_mcp_server.py
```

`.mcp.json` for MCP clients:

```json
{
  "mcpServers": {
    "tme": {
      "command": "python",
      "args": ["tme_mcp_server.py"],
      "cwd": "/path/to/tme-mcp",
      "env": {
        "TME_APP_TOKEN": "your-token",
        "TME_APP_SECRET": "your-secret",
        "TME_COUNTRY": "AT",
        "TME_CURRENCY": "EUR"
      }
    }
  }
}
```

Locale env vars are optional -- defaults are `PL`/`EN`/`PLN` (see [Configuration](#configuration)).

## Tools

### Search & Browse

| Tool | Description |
|------|-------------|
| `search_products` | Search products by keyword, part number, or category; paginated, sortable |
| `get_categories` | Browse the product category tree or flat list |
| `search_parameters` | Get available filter parameters and values for a category |
| `get_manufacturers` | List manufacturers, optionally per category |

### Product Details

| Tool | Description |
|------|-------------|
| `get_products` | Full product details for up to 50 symbols or manufacturer part numbers |
| `get_parameters` | Technical specifications/attributes for up to 50 symbols |
| `get_product_files` | Datasheets, photos, and documents for up to 50 symbols |
| `get_similar_products` | Find alternative/similar parts |
| `get_related_products` | Find related parts (accessories, complementary items) |

### Pricing & Stock

| Tool | Description |
|------|-------------|
| `get_prices` | Pricing with volume discount tiers for up to 50 symbols |
| `get_stocks` | Inventory levels for up to 50 symbols |
| `get_prices_and_stocks` | Combined pricing and stock in a single call |

### Other

| Tool | Description |
|------|-------------|
| `get_delivery_time` | Estimated delivery time for up to 50 symbols |
| `generate_tme_url` | Generate a product page URL for a TME symbol |

## Configuration

All settings are controlled via environment variables. In Docker MCP Toolkit mode, these are set in the catalog `env` block or as secrets. In standalone mode, use a `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `TME_APP_TOKEN` | *(required)* | API token from developers.tme.eu |
| `TME_APP_SECRET` | *(required)* | App secret for the OAuth token exchange |
| `TME_COUNTRY` | `PL` | Country code (e.g. `AT`, `DE`, `PL`) |
| `TME_LANGUAGE` | `EN` | Language code, sent as `Accept-Language` |
| `TME_CURRENCY` | `PLN` | Currency code (e.g. `EUR`, `PLN`) |

## Authentication

TME API v2 uses OAuth 2.0 client credentials. The server exchanges your App Token and App Secret for a short-lived bearer token (5 minutes) and refreshes it automatically.

## Troubleshooting

**Gateway shows 0 tools:** Verify the `tools` list in your catalog matches the tool names in the [Tools](#tools) section above.

**403 Access denied on every call:** Your application is a v2 application but the server is an old (HMAC, legacy API) build. Rebuild the image from this repository.

**Catalog changes not taking effect:** Re-run `docker mcp catalog import ~/.docker/mcp/catalogs/custom.yaml` after editing the catalog file. Restart your MCP client afterward.

**Secret errors:** Verify your credentials with `docker mcp secret list`. Secret names must be prefixed: `tme.TME_APP_TOKEN`, not `TME_APP_TOKEN`.

## License

MIT License -- see [LICENSE](LICENSE).
