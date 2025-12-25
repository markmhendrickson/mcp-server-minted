# Minted MCP Server Setup

## Quick Start

1. **Install dependencies:**
   ```bash
   cd mcp-servers/minted
   pip install -r requirements.txt
   ```

2. **Configure credentials** (choose one):
   
   **Option A: 1Password (Recommended)**
   - Ensure `scripts/credentials.py` is available
   - Store Minted credentials in 1Password with title "Minted.com"
   - No environment variables needed
   
   **Option B: Environment Variables**
   ```bash
   export minted_email="your@email.com"
   export minted_password="yourpassword"
   ```
   
   **Option C: Interactive Prompt**
   - Server will prompt for credentials if not found

3. **Add to Cursor MCP configuration:**
   
   Edit `~/.cursor/mcp.json` or Cursor settings:
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

4. **Restart Cursor** to load the MCP server

## Testing

Test the server manually:

```bash
cd mcp-servers/minted
python minted_mcp_server.py
```

Then send MCP protocol messages via stdin (or use an MCP client).

## Troubleshooting

### Authentication Fails

- Verify credentials are correct
- Check if Minted.com login page structure has changed
- Try running `minted-export/export_contacts.py` manually to test authentication

### API Endpoints Not Found

- Minted API structure may have changed
- Check browser Network tab when accessing Minted manually
- Update endpoints in `minted_mcp_server.py` if needed

### Selenium Issues

- Ensure Chrome/Chromium is installed
- `webdriver-manager` will download ChromeDriver automatically
- For headless issues, try removing `--headless` flag temporarily

## Dependencies

- `mcp>=0.9.0` - MCP SDK
- `requests>=2.31.0` - HTTP requests
- `selenium>=4.15.0` - Browser automation
- `webdriver-manager>=4.0.0` - ChromeDriver management

## Security Notes

- Credentials are never logged or exposed
- Session cookies are stored in memory only
- All network requests are to `minted.com` domains only
- See `minted-export/SECURITY_ASSESSMENT.md` for security analysis

