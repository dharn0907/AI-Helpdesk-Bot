"""Synchronous MCP client for the AI Helpdesk Bot."""

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_SERVER_URL = "http://127.0.0.1:8001/mcp"


async def _async_search_solved_tickets(
    user_message: str,
    intent: str,
    company_id: int,
    chatbot_id: int,
):
    async with streamablehttp_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            result = await session.call_tool(
                "search_solved_tickets",
                arguments={
                    "user_message": user_message,
                    "intent": intent,
                    "company_id": company_id,
                    "chatbot_id": chatbot_id,
                },
            )

            if result.isError:
                print("MCP tool execution returned an error.")
                return None

            structured = getattr(result, "structuredContent", None)

            if structured:
                return structured

            for item in result.content:
                if item.type == "text":
                    try:
                        return json.loads(item.text)
                    except json.JSONDecodeError:
                        pass

            return None


def search_solved_tickets_via_mcp(
    user_message: str,
    intent: str,
    company_id: int,
    chatbot_id: int,
):
    """Call MCP from the synchronous FastAPI chatbot endpoint."""

    try:
        return asyncio.run(
            _async_search_solved_tickets(
                user_message=user_message,
                intent=intent,
                company_id=company_id,
                chatbot_id=chatbot_id,
            )
        )

    except Exception as exc:
        import traceback
        
        print(f"MCP historical solution search failed: {exc}")
        traceback.print_exc()
        return none
    