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

## 🔌 MCP setup
Here is an example config file which you can use to set up Merge MCP.

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

### Example Claude Desktop configuration

1. Ensure you have `uvx` installed

2. Download [Claude Desktop](https://claude.ai/download) from the official website

3. Once downloaded, open the app and follow the instructions to set up your account

4. Navigate to **Settings → Developer → Edit Config**. This should open a file named `claude_desktop_config.json` in a text editor.

5. Copy the MCP server setup JSON above and paste it into the text editor

6. Replace `your_api_key` and `your_account_token` with your actual Merge API key and Linked Account token. You will also need to replace `uvx` with the absolute path to the command in the config file (i.e. `/Users/username/.local/bin/uvx`). You can find the absolute path by running `which uvx` through your terminal.

7. Save the config file

8. Restart Claude Desktop to see your tools. The tools may take a minute to appear

### Example Python client configuration

1. Setting up your environment

```bash
# Create project directory
mkdir mcp-client
cd mcp-client

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Unix or MacOS:
source .venv/bin/activate

# Install required packages
pip install mcp uv anthropic python-dotenv

# Create our main file
touch client.py
```

2. Setting up your API keys

```bash
# Add your ANTHROPIC_API_KEY and MERGE_API_KEY to .env
echo "ANTHROPIC_API_KEY=<your Anthropic key here>" >> .env
echo "MERGE_API_KEY=<your Merge key here>" >> .env

# Add .env file to .gitignore
echo ".env" >> .gitignore
```

3. Create a `client.py` file and add the following code

```python
import os
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    # Methods will go here
```

4. Add a `connect_to_server` function to the MCPClient class

```python
async def connect_to_server(self, linked_account_token: str):
    """Connect to an MCP server
    Args:
        linked_account_token: The token for the associated Linked Account
    """

    server_params = StdioServerParameters(
        command="uvx",
        args=["merge-mcp"],
        env={
            "MERGE_API_KEY": os.getenv("MERGE_API_KEY"),
            "MERGE_ACCOUNT_TOKEN": linked_account_token
        }
    )

    stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
    self.stdio, self.write = stdio_transport
    self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

    await self.session.initialize()

    # List available tools
    response = await self.session.list_tools()
    tools = response.tools
    print("\nConnected to server with tools:", [tool.name for tool in tools])
```

5. Add a `process_query` function to the MCPClient class

```python
async def process_query(self, query: str) -> str:
    """Process a query using Claude and available tools"""
    messages = [
        {
            "role": "user",
            "content": query
        }
    ]

    response = await self.session.list_tools()
    available_tools = [{
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.inputSchema
    } for tool in response.tools]

    # Initial Claude API call
    response = self.anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1000,
        messages=messages,
        tools=available_tools
    )

    # Process response and handle tool calls
    final_text = []
    assistant_message_content = []
    for content in response.content:
        if content.type == 'text':
            final_text.append(content.text)
            assistant_message_content.append(content)

        elif content.type == 'tool_use':
            tool_name = content.name
            tool_args = content.input

            # Get confirmation for tool call execution
            confirmation = input(f"Do you want to call tool '{tool_name}' with arguments {tool_args}? (y/n): ").strip().lower()
            if confirmation.startswith('y'):
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                final_text.append(response.content[0].text)

            else:
                final_text.append(f"[Skipped calling tool {tool_name} with args {tool_args}]")

    return "\n".join(final_text)
```

6. Add a `chat_loop` function to the MCPClient class

```python
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

            if query.lower() == 'quit':
                break

            response = await self.process_query(query)
            print("\n" + response)

        except Exception as e:
            print(f"\nError: {str(e)}")
```

7. Add a `cleanup` function to the MCPClient class

```python
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
```

8. Add a `main` function to the `client.py` file as the main entry point

```python
async def main():
    client = MCPClient()
    try:
        await client.connect_to_server("<your Linked Account token here>")
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
```

9. Running the client

```bash
python client.py
```

## 🔍 Scopes

Scopes determine which tools are enabled on the MCP server and are used to control access to different parts of the Merge API. **If no scopes are specified, all available scopes will be enabled.**

When starting the server, you can specify which scopes to enable. This is done by passing the `--scopes` flag with a list of scopes.

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

Scopes in the Merge MCP server follow a specific format based on the Merge API category and common model names. Each scope is formatted as:

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

You can combine multiple scopes to grant different permissions.

### Important Notes on Scope Availability

The available scopes depend on your Merge API account configuration and the models the Linked Account has access to. Scopes must be cross-referenced with enabled scopes on your Linked Account:

- **Category Mismatch**: If you specify a scope for a category that doesn't match your Linked Account (e.g., using `ats.Job` with an HRIS Linked Account), no tools for that scope will be returned.

- **Permission Mismatch**: If you request a permission that isn't enabled for your Linked Account (e.g., using `hris.Employee:write` when only read access is enabled), tools requiring that permission won't be returned.

- **Validation**: The server will automatically validate your requested scopes against what's available in your Linked Account and will only enable tools for valid, authorized scopes.

Scopes typically correspond to different models or entity types in the Merge API, and they control both read and write access to these entities.

## 🚀 Available Tools

The Merge MCP server provides access to various Merge API endpoints as tools. The available tools depend on your Merge API category (HRIS, ATS, etc.) and the scopes you have enabled.

Tools are dynamically generated based on your Merge API schema and include operations for:

- Retrieving entity details
- Listing entities
- Creating new entities
- Updating existing entities
- And more, based on your specific Merge API configuration

**Note:** Download tools are not currently supported. This is a known limitation and will be addressed in a future release.

## 🔑 Environment Variables

The following environment variables are used by the Merge MCP server:

- `MERGE_API_KEY`: Your Merge API key
- `MERGE_ACCOUNT_TOKEN`: Your Merge Linked Account token
- `MERGE_TENANT` (Optional): The Merge API tenant. Valid values are `US`, `EU`, and `APAC`. Defaults to `US`.