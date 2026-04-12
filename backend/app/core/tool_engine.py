"""
Tool/Action execution engine for RAZE AI OS.
Handles API calls, workflow automation, and tool orchestration.
"""

import json
import logging
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_exponential
import jsonschema

from app.models.tool import Tool, ToolExecution
from app.config import get_settings

logger = logging.getLogger(__name__)


class ToolEngine:
    """Tool execution and orchestration engine."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.settings = get_settings()
        self.http_timeout = 30.0  # 30 second timeout per tool call

    async def execute_tool(
        self,
        tool_id: str,
        input_data: Dict[str, Any],
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a tool with given input."""
        try:
            # Fetch tool definition
            stmt = select(Tool).where(Tool.id == tool_id)
            result = await self.db.execute(stmt)
            tool = result.scalar_one_or_none()

            if not tool:
                return {"error": f"Tool {tool_id} not found"}

            if not tool.is_active:
                return {"error": f"Tool {tool.name} is not active"}

            # Validate input against schema
            try:
                jsonschema.validate(input_data, tool.schema)
            except jsonschema.ValidationError as e:
                return {"error": f"Invalid input: {e.message}"}

            # Execute based on tool type
            if tool.type == "http_api":
                result_data = await self._execute_http_tool(tool, input_data)
            elif tool.type == "database":
                result_data = await self._execute_database_tool(tool, input_data)
            else:
                result_data = {"error": f"Unknown tool type: {tool.type}"}

            # Log execution
            execution = ToolExecution(
                id=str(uuid.uuid4()),
                tool_id=tool_id,
                conversation_id=conversation_id,
                input_data=input_data,
                output_data=result_data,
                status="success" if "error" not in result_data else "error",
                error_message=result_data.get("error", None),
                executed_at=datetime.utcnow()
            )

            self.db.add(execution)

            # Update tool usage stats
            tool.usage_count = (tool.usage_count or 0) + 1
            if "error" not in result_data:
                tool.success_rate = ((tool.success_rate or 0) * (tool.usage_count - 1) + 1) / tool.usage_count

            await self.db.commit()

            logger.info(f"Executed tool {tool.name} - status: {execution.status}")
            return result_data

        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return {"error": str(e)}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _execute_http_tool(self, tool: Tool, input_data: Dict) -> Dict:
        """Execute HTTP API tool with retry."""
        try:
            # Build headers
            headers = {"Content-Type": "application/json"}

            # Add authentication
            if tool.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {tool.auth_config.get('token', '')}"
            elif tool.auth_type == "api_key":
                key_name = tool.auth_config.get("key_name", "X-API-Key")
                headers[key_name] = tool.auth_config.get("key_value", "")
            elif tool.auth_type == "basic":
                import base64
                creds = f"{tool.auth_config.get('username', '')}:{tool.auth_config.get('password', '')}"
                encoded = base64.b64encode(creds.encode()).decode()
                headers["Authorization"] = f"Basic {encoded}"

            # Prepare request
            url = tool.endpoint_url
            method = tool.method.upper()

            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                if method == "GET":
                    response = await client.get(url, params=input_data, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=input_data, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=input_data, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"error": f"Unsupported HTTP method: {method}"}

                response.raise_for_status()

                # Parse response
                try:
                    return response.json()
                except:
                    return {"result": response.text}

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing tool: {e.response.status_code}")
            return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except httpx.TimeoutException:
            logger.error("Tool execution timeout")
            return {"error": "Tool execution timeout (>30s)"}
        except Exception as e:
            logger.error(f"Error executing HTTP tool: {e}")
            return {"error": str(e)}

    async def _execute_database_tool(self, tool: Tool, input_data: Dict) -> Dict:
        """Execute database tool (placeholder for future database query execution)."""
        return {"error": "Database tools not yet implemented"}

    async def validate_input(self, schema: Dict, input_data: Dict) -> tuple[bool, Optional[str]]:
        """Validate input against JSON schema."""
        try:
            jsonschema.validate(input_data, schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, e.message

    async def select_tool(
        self,
        available_tools: List[Tool],
        intent: str,
        context: str
    ) -> Optional[Tool]:
        """Select best tool for the task using LLM heuristics."""
        if not available_tools:
            return None

        # Simple heuristics: match tool name/description with intent
        intent_lower = intent.lower()

        for tool in available_tools:
            if intent_lower in tool.name.lower() or intent_lower in tool.description.lower():
                if tool.is_active:
                    return tool

        # If no exact match, return first active tool
        for tool in available_tools:
            if tool.is_active:
                return tool

        return None

    def parse_tool_calls(self, llm_response: Dict) -> List[Dict]:
        """Parse OpenAI-format function calls from LLM response."""
        try:
            if "tool_calls" not in llm_response:
                return []

            parsed = []
            for call in llm_response["tool_calls"]:
                if call.get("type") == "function":
                    parsed.append({
                        "id": call.get("id", str(uuid.uuid4())),
                        "tool_id": call["function"]["name"],
                        "arguments": json.loads(call["function"]["arguments"])
                    })

            return parsed
        except Exception as e:
            logger.error(f"Error parsing tool calls: {e}")
            return []

    def format_tool_result(
        self,
        tool_name: str,
        result: Dict,
        format_type: str = "text"  # text, table, card
    ) -> str:
        """Format tool result for display."""
        try:
            if "error" in result:
                return f"❌ {tool_name} Error: {result['error']}"

            if format_type == "table":
                # TODO: Implement table formatting
                return json.dumps(result, indent=2)
            elif format_type == "card":
                # TODO: Implement card formatting
                return json.dumps(result, indent=2)
            else:
                return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Error formatting tool result: {e}")
            return str(result)

    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get tool by ID."""
        stmt = select(Tool).where(Tool.id == tool_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tools(self, active_only: bool = True) -> List[Tool]:
        """List all tools."""
        stmt = select(Tool)
        if active_only:
            stmt = stmt.where(Tool.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_tool(
        self,
        name: str,
        description: str,
        tool_type: str,
        schema: Dict,
        endpoint_url: Optional[str] = None,
        method: str = "POST",
        auth_type: Optional[str] = None,
        auth_config: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Tool:
        """Create a new tool."""
        try:
            tool = Tool(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                type=tool_type,
                schema=schema,
                endpoint_url=endpoint_url,
                method=method,
                auth_type=auth_type,
                auth_config=auth_config or {},
                is_active=True,
                tags=tags or [],
                usage_count=0,
                success_rate=1.0
            )
            self.db.add(tool)
            await self.db.flush()
            return tool
        except Exception as e:
            logger.error(f"Error creating tool: {e}")
            raise
