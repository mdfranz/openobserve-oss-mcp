# Improvements Summary

This document summarizes the enhancements made to the OpenObserve MCP server codebase.

## 1. Environment Variable Validation

### Problem
The server would start with invalid configuration and fail with cryptic errors during runtime.

### Solution
Added comprehensive validation in `main.py` with clear, actionable error messages:

- **URL validation**: Ensures `ZO_BASE_URL` has proper scheme and host
- **Port validation**: Validates port numbers are in range 1-65535
- **Authentication validation**: Checks that either access key OR email/password are provided with helpful error messages
- **Numeric parameter validation**: Validates timeout, max-rows, and max-chars are positive integers

### Benefits
- **Fail fast**: Configuration errors are caught at startup, not during requests
- **Clear error messages**: Users get actionable guidance on how to fix configuration issues
- **Self-documenting**: Error messages reference environment variables and provide examples

### Example Error Messages
```
Configuration error: Authentication required. Provide either:
  1. ZO_ACCESS_KEY environment variable (recommended), or
  2. Both ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD

See .env.example for configuration template.
```

## 2. Logging Enhancements

### Problem
- Fixed logging level (INFO)
- Inconsistent log formatting
- Difficult to debug issues without detailed logs

### Solution
Added configurable logging via `MCP_LOG_LEVEL` environment variable:

- **Configurable levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Structured logging**: Consistent format with timestamps and module names
- **Debug mode**: More detailed format with line numbers when LOG_LEVEL=DEBUG
- **Context-aware logging**: Logs include request parameters, SQL queries, and timing information

### Configuration
```bash
# In .env or shell
export MCP_LOG_LEVEL=DEBUG  # For detailed troubleshooting
export MCP_LOG_LEVEL=INFO   # Default, recommended for production
export MCP_LOG_LEVEL=ERROR  # Minimal logging
```

### Enhanced Logging Coverage
- Server startup/shutdown
- Configuration validation
- Authentication setup
- Request/response details (with SQL queries)
- Error conditions with full context
- Performance metrics (future: timing)

### Log Format
```
# INFO level
2025-02-13 14:30:15 [INFO] mcp_server_openobserve.main - Configuration validated: transport=http, base_url=http://127.0.0.1:5080, org=default, auth=access_key

# DEBUG level
2025-02-13 14:30:15 [DEBUG] mcp_server_openobserve.client:45 - OpenObserveClient initialized: base_url=http://127.0.0.1:5080, org=default, timeout=30s
```

## 3. Error Handling Improvements

### Problem
- Generic exceptions made troubleshooting difficult
- Poor error messages didn't indicate root cause
- No distinction between different error types (auth, connection, API errors)

### Solution
Created custom exception hierarchy for better error categorization:

```python
OpenObserveError (base)
├── ConfigurationError      # Invalid config/env vars
├── AuthenticationError     # Auth failures (401, 403)
├── OpenObserveConnectionError  # Network/connection issues
└── APIError               # API-level errors (with status code)
```

### Error Handling Features

#### Specific HTTP Status Handling
- **401 Unauthorized**: Clear message about credential verification
- **403 Forbidden**: Indicates permission issues with organization
- **404 Not Found**: Helps identify incorrect resource paths
- **5xx Server Errors**: Points to OpenObserve server issues

#### Network Error Handling
- **Timeout errors**: Suggests increasing `ZO_TIMEOUT` and checking connectivity
- **Connection errors**: Verifies URL and server availability
- **Generic request errors**: Catches and logs unexpected network issues

#### Enhanced Error Messages
```python
# Before
RuntimeError: HTTP 401: Unauthorized

# After
AuthenticationError: Authentication failed. Verify ZO_ACCESS_KEY or ZO_ROOT_USER_EMAIL/PASSWORD credentials.
```

```python
# Before
RuntimeError: Connection refused

# After
OpenObserveConnectionError: Failed to connect to OpenObserve at http://127.0.0.1:5080. Verify the URL and that OpenObserve is running.
```

### Error Context
APIError exceptions now include:
- HTTP status code
- Response body (for debugging)
- Helpful guidance on resolution

## 4. Input Validation

### Added Validation For

#### SQL Queries
- Rejects empty/whitespace-only queries
- Validates time range parameters (hours must be positive)

#### API Paths
- Path traversal protection (rejects "..")
- URL scheme/host validation
- Whitelist-based path validation

#### Parameters
- Size and offset bounds checking
- Key-value pair format validation
- Query parameter sanitization

## 5. Updated Configuration Documentation

Enhanced `.env.example` with:
- New `MCP_LOG_LEVEL` variable
- Better comments explaining each option
- Default values documented
- Security guidance for tokens

## Files Modified

### Core Changes
1. **src/mcp_server_openobserve/main.py**
   - Added validation functions
   - Enhanced startup logging
   - Better error handling for server lifecycle

2. **src/mcp_server_openobserve/client.py**
   - Custom exception classes
   - Detailed error messages per HTTP status
   - Network error handling with timeouts
   - Request/response logging

3. **src/mcp_server_openobserve/server.py**
   - Configurable logging setup
   - Input validation for all tools
   - Error handling in tool functions
   - Structured logging throughout

4. **src/mcp_server_openobserve/__init__.py**
   - Export custom exceptions for external use

### Documentation
5. **.env.example**
   - Added logging configuration
   - Documented all tuning parameters

## Testing the Improvements

### Validate Configuration Errors
```bash
# Missing authentication
unset ZO_ACCESS_KEY ZO_ROOT_USER_EMAIL ZO_ROOT_USER_PASSWORD
uv run mcp-server-openobserve
# Should fail with clear auth error message

# Invalid URL
export ZO_BASE_URL="not-a-url"
uv run mcp-server-openobserve
# Should fail with URL validation error

# Invalid port
export MCP_PORT=99999
uv run mcp-server-openobserve --transport http
# Should fail with port range error
```

### Test Logging Levels
```bash
# Debug mode
MCP_LOG_LEVEL=DEBUG uv run mcp-server-openobserve

# Quiet mode
MCP_LOG_LEVEL=ERROR uv run mcp-server-openobserve
```

### Test Error Handling
```bash
# Wrong credentials
export ZO_ACCESS_KEY="invalid"
uv run mcp-server-openobserve
# Make a request - should get clear auth error

# Wrong URL
export ZO_BASE_URL="http://localhost:9999"
uv run mcp-server-openobserve
# Make a request - should get clear connection error

# Timeout
export ZO_TIMEOUT=1
uv run mcp-server-openobserve
# Make a slow query - should get timeout error with suggestion
```

## Future Improvements

### Potential Enhancements
1. **Metrics**: Add timing metrics for requests
2. **Retry logic**: Automatic retry for transient failures
3. **Health checks**: Validate OpenObserve connectivity at startup
4. **Connection pooling**: Reuse HTTP connections for better performance
5. **Async support**: Non-blocking I/O for concurrent requests
6. **Structured logging**: JSON-formatted logs for log aggregation systems
7. **Rate limiting**: Protect against excessive API calls
8. **Caching**: Cache stream lists and metadata

### Monitoring Recommendations
When deploying in production, consider:
- Centralizing logs (ELK, CloudWatch, etc.)
- Setting up alerts on ERROR/CRITICAL logs
- Monitoring request latencies
- Tracking authentication failures

## Backward Compatibility

All changes are **backward compatible**:
- Existing environment variables work as before
- Default behavior unchanged (INFO logging)
- New features are opt-in via environment variables
- API and tool interfaces unchanged

## Migration Guide

No migration needed! To use new features:

1. **Enable debug logging**:
   ```bash
   export MCP_LOG_LEVEL=DEBUG
   ```

2. **Handle specific exceptions** (optional, for custom scripts):
   ```python
   from mcp_server_openobserve import (
       AuthenticationError,
       OpenObserveConnectionError,
       ConfigurationError,
       APIError
   )

   try:
       client.search(...)
   except AuthenticationError:
       # Handle auth issues
   except OpenObserveConnectionError:
       # Handle network issues
   except APIError as e:
       # Handle API errors, access e.status_code
   ```

## Summary

These improvements make the OpenObserve MCP server:
- **More robust**: Validates configuration and handles errors gracefully
- **Easier to debug**: Configurable logging with clear, contextual messages
- **More user-friendly**: Helpful error messages guide users to solutions
- **Production-ready**: Proper error handling and logging for operational use

All enhancements follow Python best practices and maintain backward compatibility.
