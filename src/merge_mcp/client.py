import uuid
import asyncio
import json
import logging
import os
from typing import Any, ClassVar, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

from merge_mcp.constants import READ_SCOPE, WRITE_SCOPE
from merge_mcp.types import CommonModelScope

logger = logging.getLogger(__name__)

class MergeClientError(Exception):
    """Exception raised for errors in the Merge API client."""
    pass


class MergeAPIClient:
    """
    A client wrapper class for interacting with the Merge API.
    
    This class handles authentication and provides methods for making
    requests to various Merge API endpoints.
    
    This class implements the Singleton pattern, ensuring only one instance
    exists throughout the application.
    """

    _instance: ClassVar[Optional['MergeAPIClient']] = None
    
    def __new__(cls, api_key: Optional[str] = None, account_token: Optional[str] = None):
        """
        Create a new instance of MergeAPIClient if one doesn't exist already.
        If an instance already exists, return that instance.
        
        Args:
            api_key: The Merge API key. If not provided, will try to get from environment variable.
            account_token: The Merge account token. If not provided, will try to get from environment variable.
        """
        if cls._instance is None:
            cls._instance = super(MergeAPIClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, api_key: Optional[str] = None, account_token: Optional[str] = None):
        """
        Initialize the Merge API client.
        
        Args:
            api_key: The Merge API key. If not provided, will try to get from environment variable.
            account_token: The Merge account token. If not provided, will try to get from environment variable.
        """
        # Only initialize once
        if getattr(self, '_initialized', False):
            return
            
        # Initialize fields
        self._api_key = api_key or os.getenv("MERGE_API_KEY")
        self._account_token = account_token or os.getenv("MERGE_ACCOUNT_TOKEN")
        self._tenant = os.getenv("MERGE_TENANT").upper() if os.getenv("MERGE_TENANT") else "US"
        self._session_id = str(uuid.uuid4())
        self._account_info = None
        self._initialized = True
        self._category = None
        self._base_url = None
        
        if not self._api_key:
            raise MergeClientError("Merge API key is required. Set MERGE_API_KEY environment variable or pass it to the constructor.")
        
        if not self._account_token:
            raise MergeClientError("Merge account token is required. Set MERGE_ACCOUNT_TOKEN environment variable or pass it to the constructor.")

        # Set base URL based on tenant
        if self._tenant == "US":
            self._base_url = "https://api.merge.dev/"
        elif self._tenant == "EU":
            self._base_url = "https://api-eu.merge.dev/"
        elif self._tenant == "APAC":
            self._base_url = "https://api-ap.merge.dev/"
        else:
            raise ValueError(f"Invalid tenant: {self._tenant}")

    
    @classmethod
    def get_instance(cls, api_key: Optional[str] = None, account_token: Optional[str] = None) -> 'MergeAPIClient':
        """
        Get the singleton instance of the MergeAPIClient.
        
        Args:
            api_key: The Merge API key. If not provided, will try to get from environment variable.
            account_token: The Merge account token. If not provided, will try to get from environment variable.
            
        Returns:
            The singleton instance of MergeAPIClient.
        """
        return cls(api_key, account_token)
        
    @classmethod
    async def get_initialized_instance(cls, api_key: Optional[str] = None, account_token: Optional[str] = None) -> 'MergeAPIClient':
        """
        Get the singleton instance of the MergeAPIClient and initialize account information.
        
        This method ensures that the client has fetched account details and determined
        the category associated with the account.
        
        Args:
            api_key: The Merge API key. If not provided, will try to get from environment variable.
            account_token: The Merge account token. If not provided, will try to get from environment variable.
            
        Returns:
            The initialized singleton instance of MergeAPIClient.
        """
        instance = cls(api_key, account_token)
        await instance.initialize_account_info()
        return instance
    
    
    async def get_account_details(self) -> Dict[str, Any]:
        """
        Get account details from the Merge API.
        
        This method will return the correct account information
        with the actual category in the response.
        
        Returns:
            A dictionary containing the account details and the correct category
        """
        try:
            response = await self._make_request("GET", f"/api/hris/v1/account-details")
            return {"category": response["category"], "details": response}
        except Exception as e:
            raise MergeClientError(f"Failed to get account details: {str(e)}")
            
    async def initialize_account_info(self) -> None:
        """
        Initialize account information including determining the category.
        This method should be called once during application startup.
        """
        if self._account_info is not None:
            return
            
        try:
            account_info = await self.get_account_details()
            self._account_info = account_info.get("details", {})
            self._category = account_info.get("category")
        except MergeClientError as e:
            raise MergeClientError(f"Failed to initialize account info: {str(e)}")
        
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get the account information.
        
        Returns:
            The account information as a dictionary.
        """
        return self._account_info or {}
    

    async def fetch_enabled_scopes(self) -> List[CommonModelScope]:
        """
        Fetch the list of enabled scopes for the current account and return them as a list of CommonModelScope objects.
        
        Returns:
            A list of CommonModelScope objects representing the enabled scopes.
            
        Raises:
            MergeClientError: If the request fails or the response is invalid.
        """
        try:
            response = await self._make_request("GET", "linked-account-scopes", with_retry=True, max_retries=2)
            if "common_models" not in response:
                raise MergeClientError("Failed to get enabled scopes")
            
            scopes = []
            for common_model in response["common_models"]:
                model_permissions = common_model.get("model_permissions", {})
                scopes.append(CommonModelScope(
                    model_name=common_model["model_name"],
                    is_read_enabled=model_permissions.get(READ_SCOPE.upper(), {}).get("is_enabled", False),
                    is_write_enabled=model_permissions.get(WRITE_SCOPE.upper(), {}).get("is_enabled", False)
                ))
            return scopes
        except MergeClientError:
            raise MergeClientError("Failed to get enabled scopes")
    
    async def get_openapi_schema(self) -> Dict[str, Any]:
        """
        Retrieve the OpenAPI schema from the Merge API.
        
        This method fetches the OpenAPI schema which describes the API endpoints,
        models, and operations available for the current category.
        
        Returns:
            A dictionary containing the OpenAPI schema.
            
        Raises:
            MergeClientError: If the request fails or the response is invalid.
        """
        try:
            response = await self._make_request("GET", "schema", unauthorized=True, with_retry=True)
            return response
        except MergeClientError as e:
            raise MergeClientError(f"Failed to get OpenAPI schema: {str(e)}") from e
    
    async def call_associated_meta_endpoint(self, endpoint: str, method: str) -> Dict[str, Any]:
        """
        Call the associated meta endpoint for a given endpoint and method.
        
        Args:
            endpoint: The endpoint to call the meta endpoint for.
            method: The HTTP method to use for the meta endpoint.
            
        Returns:
            The response from the meta endpoint.
        """
        meta_endpoint = self._construct_meta_endpoint(endpoint, method)
        response = await self._make_request("GET", meta_endpoint)
        return response
    
    def _construct_meta_endpoint(self, endpoint: str, method: str) -> str:
        """
        /meta/<method> will be inserted after the first path in the endpoint

        i.e. /tickets -> /tickets/meta/{method}
             /tickets/{id} -> /tickets/meta/{method}/{id}
        """
        # split endpoint into paths
        paths = endpoint.split("/", 2)
        # insert /meta/{method} after the first path
        if len(paths) < 3:
            return f"{endpoint}/meta/{method}"
        return f"/{paths[1]}/meta/{method}/{paths[2]}"
    
    def _get_headers(self, additional_headers: Optional[Dict[str, str]] = None, unauthorized: bool = False) -> Dict[str, str]:
        """
        Get the headers for API requests.
        
        Args:
            additional_headers: Additional headers to include in the request.
            unauthorized: Whether the request should be made without authentication. This leaves out the Authorization and X-Account-Token headers.
            
        Returns:
            Dict containing the headers.
        """
        headers = {}
        
        if not unauthorized:
            headers["Authorization"] = f"Bearer {self._api_key}"
            headers["X-Account-Token"] = self._account_token

        headers["MCP-Session-ID"] = self._session_id
        
        if additional_headers:
            headers.update(additional_headers)
            
        return headers

    def _format_url(self, endpoint: str) -> str:
        """
        Format the endpoint URL based on the category.

        Args:
            endpoint: The endpoint to format.
            
        Returns:
            The formatted endpoint URL.
        """
        if endpoint.startswith('/api/'):
            # Full path is provided, use as is
            full_endpoint = endpoint
        elif self._category is not None:
            # Relative path with category available, append to category base path
            if endpoint.startswith('/'):
                # Remove leading slash if present
                endpoint = endpoint[1:]
            full_endpoint = f"/api/{self._category}/v1/{endpoint}"
        else:
            # No category available, assume endpoint is already properly formatted
            full_endpoint = endpoint
        
        return urljoin(self._base_url, full_endpoint)

    def _format_error_message(self, error_prefix: str, error_suffix: str, attempt: int, max_retries: int, method: str, url: str, params: Optional[Dict[str, Any]], data: Optional[Dict[str, Any]]):
        return f"{error_prefix}: Attempt {attempt}/{max_retries} failed for {method} request to {url} with params={params} and data={data}. {error_suffix}"
    
    async def _make_request(self,
                        method: str,
                        endpoint: str,
                        params: Optional[Dict[str, Any]] = None,
                        data: Optional[Dict[str, Any]] = None,
                        headers: Optional[Dict[str, str]] = None,
                        unauthorized: bool = False,
                        with_retry: bool = False,
                        max_retries: int = 3,
                        backoff_factor: float = 1.0,
                        timeout: float = 10.0) -> Union[Dict[str, Any], str]:
        """
        Make an asynchronous request to the Merge API with robust error handling and optional retries.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE).
            endpoint: API endpoint path. Can be:
                      - Full path starting with "/api/" (e.g., "/api/hris/v1/employees")
                      - Relative path (e.g., "employees") which will be appended to "/api/{category}/v1/"
            params: Query parameters.
            data: Request body data.
            headers: Additional headers.
            unauthorized: Whether to skip authentication headers.
            with_retry: Whether to retry the request on failure.
            max_retries: Maximum number of attempts (including the first).
            backoff_factor: A factor for calculating exponential backoff delay.
            timeout: Optional timeout for the request.

        Returns:
            Response data as a dictionary if JSON decodes successfully, otherwise as raw text.

        Raises:
            MergeClientError: If the request fails after the allowed number of retries.
        """
        url = self._format_url(endpoint)
        # Combine default headers with any provided ones.
        headers = self._get_headers(headers, unauthorized)

        logger.debug(f"Initiating {method} request to {url} with params={params} and data={data}")

        # Determine number of attempts
        attempts = max_retries if with_retry else 1
        delay = backoff_factor

        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            for attempt in range(1, attempts + 1):
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        params=params,
                        json=data,
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    # Attempt to decode JSON, if fails return raw text.
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        logger.warning(f"Response content is not in JSON format: {response.text[:100]}...")
                        return response.text

                except httpx.HTTPError as e:
                    # Build an informative error message
                    response_text = ""
                    status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
                    
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            response_text = e.response.text
                        except Exception:
                            response_text = "<could not retrieve response text>"
                    
                    error_message = self._format_error_message(f"HTTP Error {status_code}", f"Response: {response_text or str(e)}", attempt, attempts, method, url, params, data)
                    logger.error(error_message)

                    # Only retry on specific status codes if we have attempts left
                    if attempt < attempts:
                        logger.debug(f"Retrying after {delay} seconds...")
                        await asyncio.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    
                    # If this is the last attempt or not a retryable status code, raise the error
                    raise MergeClientError(error_message) from e
                    
                except Exception as e:
                    # Catch any other unexpected exceptions
                    error_message = self._format_error_message("Unexpected error", f"Error: {str(e)}", attempt, attempts, method, url, params, data)
                    logger.error(error_message)
                    
                    # If this is the last attempt, raise the error
                    if attempt == attempts:
                        raise MergeClientError(error_message) from e
                    # Otherwise, wait before retrying
                    logger.debug(f"Retrying after {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff