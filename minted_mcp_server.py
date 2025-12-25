#!/usr/bin/env python3
"""
MCP Server for Minted.com API Interactions

Provides tools for accessing Minted.com address book, orders, and delivery information.
Uses the same authentication pattern as minted-export scripts.
"""

import json
import os
import sys
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Try to import credential utility
try:
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.credentials import get_credential_by_domain
    HAS_CREDENTIALS_MODULE = True
except ImportError:
    HAS_CREDENTIALS_MODULE = False

# Initialize MCP server
app = Server("minted")

# Global session cache
_session_cache: Dict[str, Any] = {}


def get_minted_credentials() -> Tuple[str, str]:
    """Get Minted credentials from various sources."""
    # Try 1Password first
    if HAS_CREDENTIALS_MODULE:
        try:
            email, password = get_credential_by_domain("minted.com")
            return email, password
        except Exception:
            pass
    
    # Fall back to environment variables
    email = os.environ.get("minted_email")
    password = os.environ.get("minted_password")
    
    if email and password:
        return email, password
    
    raise ValueError(
        "Minted credentials not found. Set minted_email and minted_password "
        "environment variables or configure 1Password credentials."
    )


def get_authenticated_session() -> Dict[str, str]:
    """Get authenticated session cookies for Minted API."""
    cache_key = "minted_cookies"
    
    # Check cache (could be extended to persist across calls)
    if cache_key in _session_cache:
        return _session_cache[cache_key]
    
    email, password = get_minted_credentials()
    
    # Webdriver options
    options = Options()
    options.add_argument("--headless")
    service = Service(ChromeDriverManager().install())
    driver = Chrome(service=service, options=options)
    
    try:
        URL = "https://www.minted.com/login"
        driver.get(URL)
        
        # Selenium handles login form
        email_elem = driver.find_element(By.XPATH, '//*[@id="identifierMNTD"]')
        email_elem.send_keys(email)
        password_elem = driver.find_element(By.XPATH, '//*[@id="password"]')
        password_elem.send_keys(password)
        login_submit = driver.find_element(
            By.XPATH, '//*[@id="__next"]/div[3]/div/form/div[2]/div[1]/button'
        )
        login_submit.click()
        
        sleep(5)  # Wait for login to complete
        
        # Obtain cookies from selenium session
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        
        # Cache cookies
        _session_cache[cache_key] = cookies
        
        return cookies
    finally:
        driver.close()


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available Minted API tools."""
    return [
        Tool(
            name="get_minted_contacts",
            description="Get all contacts from Minted address book",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_minted_latest_delivery",
            description="Get recipients from the latest Minted card delivery/order",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_minted_orders",
            description="Get order history from Minted",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of orders to return (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "get_minted_contacts":
        try:
            cookies = get_authenticated_session()
            
            # Request address book contents as json
            response = requests.get(
                "https://addressbook.minted.com/api/contacts/contacts/?format=json",
                cookies=cookies,
                timeout=300,
            )
            response.raise_for_status()
            contacts = response.json()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "count": len(contacts),
                    "contacts": contacts,
                }, indent=2, default=str)
            )]
        except Exception as e:
            import traceback
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }, indent=2)
            )]
    
    elif name == "get_minted_latest_delivery":
        try:
            # First try API endpoints
            cookies = get_authenticated_session()
            
            # Try the groups endpoint first (discovered via diagnostic)
            # This endpoint returns groups with type "completeorder" containing recipient contact IDs
            delivery_data = None
            working_endpoint = None
            
            try:
                groups_response = requests.get(
                    "https://addressbook.minted.com/api/contacts/groups/",
                    cookies=cookies,
                    timeout=30,
                )
                if groups_response.status_code == 200:
                    groups_data = groups_response.json()
                    if isinstance(groups_data, list) and len(groups_data) > 0:
                        # Filter for completeorder type groups (these are card deliveries)
                        order_groups = [g for g in groups_data if g.get('type') == 'completeorder']
                        if order_groups:
                            # Get the most recent order (first in list, or sort by created_at)
                            latest_group = order_groups[0]
                            if len(order_groups) > 1:
                                try:
                                    latest_group = max(order_groups, key=lambda x: x.get('created_at', ''))
                                except:
                                    latest_group = order_groups[0]
                            
                            # Get contact details for recipients
                            contact_ids = latest_group.get('contacts', [])
                            individuals = latest_group.get('individuals', [])
                            
                            # If we have individuals, use those; otherwise fetch contacts by ID
                            if individuals and len(individuals) > 0:
                                recipients = individuals
                            elif contact_ids:
                                # Fetch contact details
                                contacts_response = requests.get(
                                    "https://addressbook.minted.com/api/contacts/contacts/?format=json",
                                    cookies=cookies,
                                    timeout=30,
                                )
                                if contacts_response.status_code == 200:
                                    all_contacts = contacts_response.json()
                                    # Filter contacts by IDs
                                    recipients = [c for c in all_contacts if c.get('id') in contact_ids]
                                else:
                                    recipients = []
                            else:
                                recipients = []
                            
                            # Build delivery data structure
                            delivery_data = {
                                "id": latest_group.get('id'),
                                "title": latest_group.get('title'),
                                "created_at": latest_group.get('created_at'),
                                "recipients": recipients,
                                "recipient_count": len(recipients),
                                "contact_ids": contact_ids,
                            }
                            working_endpoint = "https://addressbook.minted.com/api/contacts/groups/"
            except Exception:
                pass
            
            # Fallback: Try other endpoints if groups endpoint didn't work
            if not delivery_data:
                endpoints_to_try = [
                    ("https://www.minted.com/order/list-by-uid/", {}),
                    ("https://www.minted.com/order/list-by-uid/?format=json", {}),
                    ("https://addressbook.minted.com/api/orders/", {}),
                    ("https://addressbook.minted.com/api/orders/?format=json", {}),
                    ("https://addressbook.minted.com/api/deliveries/", {}),
                    ("https://addressbook.minted.com/api/shipments/", {}),
                    ("https://www.minted.com/api/orders/", {}),
                    ("https://www.minted.com/api/orders/?format=json", {}),
                    ("https://www.minted.com/api/deliveries/", {}),
                    ("https://www.minted.com/api/shipments/", {}),
                    ("https://addressbook.minted.com/api/addressbook/orders/", {}),
                    ("https://addressbook.minted.com/api/addressbook/deliveries/", {}),
                ]
                
                for endpoint, params in endpoints_to_try:
                    try:
                        response = requests.get(
                            endpoint,
                            cookies=cookies,
                            params=params,
                            timeout=30,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            # Check if this looks like delivery/order data
                            if isinstance(data, (list, dict)) and len(data) > 0:
                                working_endpoint = endpoint
                                delivery_data = data
                                break
                    except Exception:
                        continue
            
            # If no direct endpoint works, try getting orders list and finding the latest
            if not delivery_data:
                # Try to get orders list first (using discovered endpoint)
                orders_endpoints = [
                    "https://www.minted.com/order/list-by-uid/",
                    "https://www.minted.com/order/list-by-uid/?format=json",
                    "https://addressbook.minted.com/api/orders/?format=json",
                    "https://www.minted.com/api/orders/?format=json",
                    "https://addressbook.minted.com/api/orders/",
                ]
                for endpoint in orders_endpoints:
                    try:
                        response = requests.get(
                            endpoint,
                            cookies=cookies,
                            timeout=30,
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                # Get the first (most recent) order
                                latest_order = data[0]
                                # Try to get full order details
                                order_id = latest_order.get('id') or latest_order.get('order_id') or latest_order.get('order_number') or latest_order.get('orderId')
                                if order_id:
                                    detail_endpoints = [
                                        f"https://www.minted.com/order/detail/status/{order_id}",
                                        f"https://addressbook.minted.com/api/orders/{order_id}/?format=json",
                                        f"https://www.minted.com/api/orders/{order_id}/?format=json",
                                        f"https://addressbook.minted.com/api/orders/{order_id}/",
                                    ]
                                    for detail_endpoint in detail_endpoints:
                                        try:
                                            detail_response = requests.get(
                                                detail_endpoint,
                                                cookies=cookies,
                                                timeout=30,
                                            )
                                            if detail_response.status_code == 200:
                                                delivery_data = detail_response.json()
                                                working_endpoint = detail_endpoint
                                                break
                                        except:
                                            continue
                                if delivery_data:
                                    break
                                # If detail fetch failed, use the order summary
                                delivery_data = latest_order
                                working_endpoint = endpoint
                                break
                    except Exception:
                        continue
            
            # If API endpoints don't work, try scraping the finalize page
            if not delivery_data:
                try:
                    # Use Selenium to navigate to finalize page and extract data
                    email, password = get_minted_credentials()
                    options = Options()
                    options.add_argument("--headless")
                    service = Service(ChromeDriverManager().install())
                    driver = Chrome(service=service, options=options)
                    
                    try:
                        URL = "https://www.minted.com/login"
                        driver.get(URL)
                        
                        email_elem = driver.find_element(By.XPATH, '//*[@id="identifierMNTD"]')
                        email_elem.send_keys(email)
                        password_elem = driver.find_element(By.XPATH, '//*[@id="password"]')
                        password_elem.send_keys(password)
                        login_submit = driver.find_element(
                            By.XPATH, '//*[@id="__next"]/div[3]/div/form/div[2]/div[1]/button'
                        )
                        login_submit.click()
                        sleep(5)
                        
                        # Try to navigate to finalize page
                        finalize_urls = [
                            "https://www.minted.com/addressbook/my-account/finalize/0",
                            "https://addressbook.minted.com/my-account/finalize/0",
                            "https://www.minted.com/addressbook/finalize",
                        ]
                        
                        for finalize_url in finalize_urls:
                            try:
                                driver.get(finalize_url)
                                sleep(3)
                                
                                # Try to extract recipient data from page
                                page_text = driver.page_source
                                
                                # Try to find JSON data embedded in the page
                                import re
                                json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', page_text, re.DOTALL)
                                if json_match:
                                    try:
                                        page_data = json.loads(json_match.group(1))
                                        # Look for order/delivery data in the page state
                                        if 'orders' in page_data or 'deliveries' in page_data or 'finalize' in page_data:
                                            delivery_data = page_data
                                            working_endpoint = f"scraped_from:{finalize_url}"
                                            break
                                    except:
                                        pass
                                
                                # Try to find recipient elements on the page
                                try:
                                    recipient_elements = driver.find_elements(By.CSS_SELECTOR, "[data-recipient], .recipient, [class*='recipient'], [class*='address']")
                                    if recipient_elements:
                                        recipients_list = []
                                        for elem in recipient_elements:
                                            try:
                                                text = elem.text
                                                if text and len(text) > 10:  # Likely an address
                                                    recipients_list.append({"address": text})
                                            except:
                                                pass
                                        if recipients_list:
                                            delivery_data = {
                                                "recipients": recipients_list,
                                                "source": "scraped_from_page"
                                            }
                                            working_endpoint = f"scraped_from:{finalize_url}"
                                            break
                                except:
                                    pass
                            except Exception:
                                continue
                    finally:
                        driver.close()
                except Exception as scrape_error:
                    pass  # Fall through to error return
            
            if not delivery_data:
                endpoint_list = [e[0] if isinstance(e, tuple) else e for e in endpoints_to_try]
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Could not retrieve delivery information. No working API endpoint found and page scraping failed.",
                        "tried_endpoints": endpoint_list,
                        "suggestion": "Try accessing https://www.minted.com/addressbook/my-account/finalize/0 manually to view your latest delivery",
                    }, indent=2)
                )]
            
            # Handle different response formats
            if isinstance(delivery_data, list):
                # Find the most recent by date
                latest = delivery_data[0]
                if len(delivery_data) > 1:
                    try:
                        latest = max(delivery_data, key=lambda x: x.get('created_at', x.get('date', x.get('order_date', ''))))
                    except:
                        latest = delivery_data[0]
            elif isinstance(delivery_data, dict):
                latest = delivery_data
            else:
                latest = {"raw_data": delivery_data}
            
            # Extract recipients - if delivery_data already has recipients (from groups endpoint), use them
            recipients = []
            if 'recipients' in latest and latest['recipients']:
                recipients = latest['recipients'] if isinstance(latest['recipients'], list) else [latest['recipients']]
            # Otherwise try other field names
            elif 'addresses' in latest:
                recipients = latest['addresses'] if isinstance(latest['addresses'], list) else [latest['addresses']]
            elif 'contacts' in latest:
                recipients = latest['contacts'] if isinstance(latest['contacts'], list) else [latest['contacts']]
            elif 'recipient_addresses' in latest:
                recipients = latest['recipient_addresses'] if isinstance(latest['recipient_addresses'], list) else [latest['recipient_addresses']]
            elif 'shipping_addresses' in latest:
                recipients = latest['shipping_addresses'] if isinstance(latest['shipping_addresses'], list) else [latest['shipping_addresses']]
            # Items might contain recipient info
            elif 'items' in latest:
                for item in latest['items']:
                    if 'recipient' in item:
                        recipients.append(item['recipient'])
                    elif 'address' in item:
                        recipients.append(item['address'])
                    elif 'recipient_address' in item:
                        recipients.append(item['recipient_address'])
                    elif 'shipping_address' in item:
                        recipients.append(item['shipping_address'])
            # Check if the order itself has address fields (single recipient order)
            elif any(field in latest for field in ['name', 'address1', 'address', 'recipient_name', 'shipping_name']):
                recipients = [latest]
            # If no recipients found, return the raw data structure for inspection
            if not recipients and isinstance(latest, dict):
                # Try to find any nested structures that might contain addresses
                for key, value in latest.items():
                    if isinstance(value, list) and len(value) > 0:
                        # Check if list items look like addresses/recipients
                        if isinstance(value[0], dict) and any(addr_field in value[0] for addr_field in ['name', 'address1', 'address', 'city', 'zip']):
                            recipients = value
                            break
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "endpoint": working_endpoint,
                    "delivery_date": latest.get('created_at', latest.get('date', latest.get('order_date', 'Unknown'))),
                    "order_id": latest.get('id', latest.get('order_id', latest.get('order_number', 'Unknown'))),
                    "status": latest.get('status', 'Unknown'),
                    "recipient_count": len(recipients),
                    "recipients": recipients,
                    "raw_delivery_data": latest,
                }, indent=2, default=str)
            )]
        except Exception as e:
            import traceback
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }, indent=2)
            )]
    
    elif name == "get_minted_orders":
        try:
            limit = arguments.get("limit", 10)
            cookies = get_authenticated_session()
            
            # Try various API endpoints for orders
            endpoints_to_try = [
                "https://addressbook.minted.com/api/orders/",
                "https://www.minted.com/api/orders/",
                "https://addressbook.minted.com/api/addressbook/orders/",
            ]
            
            orders_data = None
            working_endpoint = None
            
            for endpoint in endpoints_to_try:
                try:
                    response = requests.get(
                        endpoint,
                        cookies=cookies,
                        timeout=30,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, (list, dict)) and len(data) > 0:
                            working_endpoint = endpoint
                            orders_data = data
                            break
                except Exception:
                    continue
            
            if not orders_data:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Could not retrieve orders. No working API endpoint found.",
                        "tried_endpoints": endpoints_to_try,
                    }, indent=2)
                )]
            
            # Handle different response formats
            if isinstance(orders_data, list):
                # Sort by date (most recent first) and limit
                try:
                    orders_data = sorted(
                        orders_data,
                        key=lambda x: x.get('created_at', x.get('date', x.get('order_date', ''))),
                        reverse=True
                    )[:limit]
                except:
                    orders_data = orders_data[:limit]
            elif isinstance(orders_data, dict):
                orders_data = [orders_data]
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "endpoint": working_endpoint,
                    "count": len(orders_data),
                    "orders": orders_data,
                }, indent=2, default=str)
            )]
        except Exception as e:
            import traceback
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }, indent=2)
            )]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Unknown tool: {name}",
            }, indent=2)
        )]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        import traceback
        print(json.dumps({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), file=sys.stderr)
        sys.exit(1)

