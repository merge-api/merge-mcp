# Merge MCP Server

This MCP (Model Context Protocol) server provides integration between Merge API and any LLM provider supporting the MCP protocol (e.g., Claude for Desktop), allowing you to interact with your Merge data using natural language.

## ✨ Features
- Query Merge API entities using natural language
- Get information about your Merge data models and their fields
- Create and update entities through conversational interfaces
- Support for multiple Merge API categories (HRIS, ATS, etc.)

## 📦 Installation

### Prerequisites

- A Merge API key and account token
- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv)

Install `uv` with standalone installer:
```bash
# On macOS and Linux.
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows.
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

or through pip:
```bash
# With pip.
pip install uv

# With pipx.
pipx install uv
```

## 🔌 MCP Integration
Add this configuration to your MCP client config file.

In Claude Desktop, you can access the config in **Settings → Developer → Edit Config**:
```json
{
    "mcpServers": {
        "merge-mcp-server": {
            "command": "uvx",
            "args": ["merge-mcp"],
            "env": {
                "MERGE_API_KEY": "your_api_key",
                "MERGE_ACCOUNT_TOKEN": "your_account_token"
            }
        }
    }
}
```
Note: If "uvx" command does not work, try absolute path (i.e. /Users/username/.local/bin/uvx)

## 🔍 Scopes

Scopes determine which tool integrations are enabled on the MCP server. The Merge MCP Server uses scopes to control access to different parts of the Merge API. When starting the server, you can specify which scopes to enable:

```json
{
    "mcpServers": {
        "merge-mcp-server": {
            "command": "uvx",
            "args": [
                "merge-mcp",
                "--scopes",
                "ats.Job:read",
                "ats.Candidate",
                "ats.Application:write"
            ],
            "env": {
                "MERGE_API_KEY": "your_api_key",
                "MERGE_ACCOUNT_TOKEN": "your_account_token"
            }
        }
    }
}
```

### Scope Format

Scopes in the Merge MCP Server follow a specific format based on the Merge API category and common model names. Each scope is formatted as:

```
<category>.<CommonModel>:<permission>
```

Where:
- `<category>` is the Merge API category (e.g., `hris`, `ats`, `accounting`)
- `<CommonModel>` is the name of the Merge Common Model (e.g., `Employee`, `Candidate`, `Account`)
- `<permission>` is either `read` or `write` (optional - if not specified, all permissions are granted)

Examples of valid scopes:
- `hris.Employee:read` - Allows reading employee data from HRIS category
- `ats.Candidate:write` - Allows creating or updating candidate data in ATS category
- `accounting.Account` - Allows all operations on account data in Accounting category

You can combine multiple scopes to grant different permissions:

**If no scopes are specified, all available scopes will be enabled.** The available scopes depend on your Merge API account configuration and the models the Linked Account has access to.

### Important Notes on Scope Availability

Scopes must be cross-referenced with enabled scopes on your Linked Account:

- **Category Mismatch**: If you specify a scope for a category that doesn't match your Linked Account (e.g., using `ats.Job` with an HRIS Linked Account), no tools for that scope will be returned.

- **Permission Mismatch**: If you request a permission that isn't enabled for your Linked Account (e.g., using `hris.Employee:write` when only read access is enabled), tools requiring that permission won't be returned.

- **Validation**: The server will automatically validate your requested scopes against what's available in your Linked Account and will only enable tools for valid, authorized scopes.

Scopes typically correspond to different models or entity types in the Merge API, and they control both read and write access to these entities.

## 🚀 Available Tools

The Merge MCP Server provides access to various Merge API endpoints as tools. The available tools depend on your Merge API category (HRIS, ATS, etc.) and the scopes you have enabled.

Tools are dynamically generated based on your Merge API schema and include operations for:

- Retrieving entity details
- Listing entities
- Creating new entities
- Updating existing entities
- And more, based on your specific Merge API configuration

**Note:** Download tools are not currently supported. This is a known limitation and will be addressed in a future release.

## 🔑 Environment Variables

The following environment variables are used by the Merge MCP Server:

- `MERGE_API_KEY`: Your Merge API key
- `MERGE_ACCOUNT_TOKEN`: Your Merge Linked Account token
- `MERGE_TENANT`: (Optional) The Merge API tenant (US, EU, APAC). Defaults to US


# Run the server

```bash
uvx merge-mcp
```
