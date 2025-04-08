"""Unit tests for the main module."""
from unittest.mock import patch, MagicMock, AsyncMock

from merge_mcp.main import main

def test_main_with_no_scopes():
    """Test that main runs with no scopes."""
    with patch("argparse.ArgumentParser") as mock_arg_parser, \
         patch("asyncio.run", new=AsyncMock()) as mock_asyncio_run, \
         patch("merge_mcp.main.serve") as mock_serve:
        
        # Setup mock argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        # Setup mock args
        mock_args = MagicMock()
        mock_args.scopes = None
        mock_parser.parse_args.return_value = mock_args
        
        # Call function under test
        main()
        
        # Verify serve was called with None
        mock_asyncio_run.assert_called_once()
        mock_serve.assert_called_once_with(None)


def test_main_with_scopes():
    """Test that main runs with scopes."""
    with patch("argparse.ArgumentParser") as mock_arg_parser, \
         patch("asyncio.run", new=AsyncMock()) as mock_asyncio_run, \
         patch("merge_mcp.main.serve") as mock_serve:
        
        # Setup mock argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        
        # Setup mock args
        mock_args = MagicMock()
        mock_args.scopes = ["scope1", "scope2"]
        mock_parser.parse_args.return_value = mock_args
        
        # Call function under test
        main()
        
        # Verify serve was called with the scopes
        mock_asyncio_run.assert_called_once()
        mock_serve.assert_called_once_with(["scope1", "scope2"])
