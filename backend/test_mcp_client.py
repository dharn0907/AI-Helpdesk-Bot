
"""Test customer ticket history through the MCP server."""

import asyncio
import json
from mcp import Client


async def main():

    server_url = "http://127.0.0.1:8001/mcp"

    print("Connecting to AI Helpdesk MCP Server...")

    async with Client(server_url) as client:

        print("\nConnected successfully!")

        response = await client.list_tools()

        print("\nAvailable MCP tools:")

        for tool in response.tools:
            print(f"- {tool.name}: {tool.description}")

        customer_email = input(
            "\nEnter the customer email to retrieve ticket history: "
        ).strip()

        print("\nRetrieving customer ticket history...")

        result = await client.call_tool(
            "get_customer_ticket_history",
            {
                "customer_email": customer_email
            }
        )

        print("\nCustomer ticket history result:")

        for content in result.content:
            if hasattr(content, "text"):
                try:
                    data = json.loads(content.text)
                    print(json.dumps(data, indent=2))
                except json.JSONDecodeError:
                    print(content.text)

        print("\nCustomer history MCP test completed!")


if __name__ == "__main__":
    asyncio.run(main())
