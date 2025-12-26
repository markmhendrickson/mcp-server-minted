# Minted MCP Server

MCP server for interacting with Minted.com API - address book, orders, and delivery information.

## Credits

This MCP server is based on the authentication pattern from [wkarney/minted-export](https://github.com/wkarney/minted-export), a utility to export addresses from minted.com. The original repository provided the Selenium-based authentication approach that this MCP server adapts for Model Context Protocol integration.

## Features

- **Get Contacts**: Retrieve all contacts from Minted address book
- **Get Latest Delivery**: Get recipients from the most recent card delivery/order
- **Get Orders**: Get order history from Minted

## Installation

```bash
cd execution/mcp-servers/minted
pip install -r requirements.txt
```

## Configuration

### Credentials

The server supports multiple authentication methods (checked in priority order):

1. **Environment Variables** (recommended, highest priority):
   ```bash
   export MINTED_EMAIL="your@email.com"
   export MINTED_PASSWORD="yourpassword"
   ```
   Also supports lowercase: `minted_email` and `minted_password`

2. **1Password Integration** (optional, for backward compatibility):
   - Only available if parent repository structure exists
   - Configure 1Password item with URL "minted.com"
   - Add fields: "email" and "password"

**Note:** The MCP server is self-contained and portable. It does not require any specific repository structure and can be used in any project.

### Cursor Configuration

Add to your Cursor MCP settings (typically `~/.cursor/mcp.json` or Cursor settings):

**Option 1: Using environment variables (recommended):**
```json
{
  "mcpServers": {
    "minted": {
      "command": "python3",
      "args": [
        "/path/to/minted_mcp_server.py"
      ],
      "env": {
        "MINTED_EMAIL": "your@email.com",
        "MINTED_PASSWORD": "yourpassword"
      }
    }
  }
}
```

**Option 2: Using 1Password integration (if parent repo structure exists):**
```json
{
  "mcpServers": {
    "minted": {
      "command": "python3",
      "args": [
        "/path/to/minted_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

**Note:** Replace `/path/to/minted_mcp_server.py` with the actual path to the server file.

### Claude Desktop Configuration

Add to `claude_desktop_config.json` (typically `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "minted": {
      "command": "python3",
      "args": [
        "/path/to/minted_mcp_server.py"
      ],
      "env": {
        "MINTED_EMAIL": "your@email.com",
        "MINTED_PASSWORD": "yourpassword"
      }
    }
  }
}
```

**Note:** Replace `/path/to/minted_mcp_server.py` with the actual path to the server file.

## Available Tools

### `get_minted_contacts`

Get all contacts from Minted address book.

**Returns:**
- `count`: Number of contacts
- `contacts`: Array of contact objects with name, address, etc.

**Example:**
```json
{
  "success": true,
  "count": 150,
  "contacts": [
    {
      "id": 123,
      "name": "John Doe",
      "address1": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "zip": "94102"
    }
  ]
}
```

### `get_minted_latest_delivery`

Get recipients from the latest Minted card delivery/order.

**Returns:**
- `delivery_date`: Date of the delivery
- `order_id`: Order identifier
- `status`: Delivery status
- `recipient_count`: Number of recipients
- `recipients`: Array of recipient objects
- `raw_delivery_data`: Complete delivery data structure

**Example:**
```json
{
  "success": true,
  "delivery_date": "2025-12-15",
  "order_id": "12345",
  "status": "shipped",
  "recipient_count": 25,
  "recipients": [
    {
      "name": "Jane Smith",
      "address1": "456 Oak Ave",
      "city": "New York",
      "state": "NY",
      "zip": "10001"
    }
  ]
}
```

### `get_minted_orders`

Get order history from Minted.

**Parameters:**
- `limit` (optional): Maximum number of orders to return (default: 10)

**Returns:**
- `count`: Number of orders returned
- `orders`: Array of order objects

**Example:**
```json
{
  "success": true,
  "count": 10,
  "orders": [
    {
      "id": "12345",
      "created_at": "2025-12-15",
      "status": "shipped",
      "total": 125.50
    }
  ]
}
```

## Authentication

The server uses Selenium to authenticate with Minted.com and then uses session cookies for API requests. This matches the authentication pattern used in the original [minted-export](https://github.com/wkarney/minted-export) scripts.

**Note:** Authentication happens on first API call and cookies are cached for subsequent calls in the same session.

## Error Handling

The server returns structured error messages in JSON format when operations fail. Common errors include:

- Credential errors (missing email/password)
- Authentication failures
- API endpoint not found
- Network timeouts

## Security Notes

- Credentials are never logged or exposed
- Session cookies are stored in memory only
- All network requests are to `minted.com` domains only
- Use 1Password integration for secure credential management

## Troubleshooting

1. **Authentication Fails**
   - Verify credentials are correct
   - Check if Minted.com login page structure has changed
   - Try running `scripts/export_minted_contacts.py` manually to test authentication

2. **API Endpoints Not Found**
   - Minted API structure may have changed
   - Check browser Network tab when accessing Minted manually
   - Update endpoints in `minted_mcp_server.py` if needed

3. **Selenium Issues**
   - Ensure Chrome/Chromium is installed
   - `webdriver-manager` will download ChromeDriver automatically
   - For headless issues, try removing `--headless` flag temporarily

## Notes

- The server uses headless Chrome via Selenium for authentication
- Session cookies are cached in memory for the duration of the server process
- All date fields are returned as strings in ISO format
- The server runs in stdio mode for MCP communication

## License

MIT

## Support

- [GitHub Issues](https://github.com/markmhendrickson/mcp-server-minted/issues)

