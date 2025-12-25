# Minted MCP Server

MCP server for interacting with Minted.com API - address book, orders, and delivery information.

## Features

- **Get Contacts**: Retrieve all contacts from Minted address book
- **Get Latest Delivery**: Get recipients from the most recent card delivery/order
- **Get Orders**: Get order history from Minted

## Installation

```bash
cd mcp-servers/minted
pip install -r requirements.txt
```

## Configuration

### Credentials

The server uses the same credential resolution as minted-export scripts:

1. **1Password** (preferred): Configure credentials module to access "Minted.com" item
2. **Environment Variables**: Set `minted_email` and `minted_password`
3. **Interactive Prompt**: Will prompt if credentials not found

### Cursor Configuration

Add to your Cursor MCP settings:

```json
{
  "mcpServers": {
    "minted": {
      "command": "python",
      "args": [
        "$REPO_ROOT/mcp-servers/minted/minted_mcp_server.py"
      ],
      "env": {
        "minted_email": "your@email.com",
        "minted_password": "yourpassword"
      }
    }
  }
}
```

Or use 1Password integration (recommended):

```json
{
  "mcpServers": {
    "minted": {
      "command": "python",
      "args": [
        "$REPO_ROOT/mcp-servers/minted/minted_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "minted": {
      "command": "python",
      "args": [
        "$REPO_ROOT/mcp-servers/minted/minted_mcp_server.py"
      ]
    }
  }
}
```

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

The server uses Selenium to authenticate with Minted.com and then uses session cookies for API requests. This matches the authentication pattern used in the minted-export scripts.

**Note:** Authentication happens on first API call and cookies are cached for subsequent calls in the same session.

## Error Handling

The server returns structured error messages in JSON format when operations fail. Common errors include:

- Credential errors (missing email/password)
- Authentication failures
- API endpoint not found
- Network timeouts

## Notes

- The server uses headless Chrome via Selenium for authentication
- Session cookies are cached in memory for the duration of the server process
- All date fields are returned as strings in ISO format
- The server runs in stdio mode for MCP communication

