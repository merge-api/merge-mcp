from merge_mcp.server import serve

def main():
    """Merge MCP"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Merge MCP"
    )
    parser.add_argument(
        "-s", "--scopes", nargs='+', type=str,
        help="Optional list of scope names that determine which tool integrations are enabled on the MCP server. \
            Only tools associated with the specified scopes will be available; if omitted, all tools will be enabled."
    )

    args = parser.parse_args()
    if args.scopes:
        print(f"Initializing server with scopes: {args.scopes}")
    else:
        print("Initializing server with all available scopes")
    asyncio.run(serve(args.scopes))


if __name__ == "__main__":
    main()
