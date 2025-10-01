import boto3
import asyncio
from mcp import ClientSession
from mcp_lambda.client.streamable_http_sigv4 import streamablehttp_client_with_sigv4

def generate_mcp_url(agent_runtime_arn: str, region: str = "<aws-region>") -> str:
    encoded_arn = agent_runtime_arn.replace(':', '%3A').replace('/', '%2F')
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"

async def test_mcp_server():
    # Replace with your actual Agent ARN
    agent_arn = "arn:aws:bedrock-agentcore:<aws-region>:<account-id>:runtime/my_iam_mcp_server-<random-id>"
    
    mcp_url = generate_mcp_url(agent_arn, region="<aws-region>")
    print(f"Connecting to: {mcp_url}")

    session = boto3.Session()
    credentials = session.get_credentials()
    
    try:
        async with streamablehttp_client_with_sigv4(
            url=mcp_url,
            service="bedrock-agentcore",
            region="<aws-region>",
            credentials=credentials,
            timeout=120,
            terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                print("Initializing MCP session...")
                await mcp_session.initialize()
                print("MCP session initialized successfully")
                
                # List available tools
                print("\n=== Available Tools ===")
                tool_result = await mcp_session.list_tools()
                for tool in tool_result.tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Test the tools
                print("\n=== Testing add_numbers tool ===")
                result = await mcp_session.call_tool("add_numbers", {"a": 5, "b": 3})
                print(f"add_numbers(5, 3) = {result.content}")
                
                print("\n=== Testing multiply_numbers tool ===")
                result = await mcp_session.call_tool("multiply_numbers", {"a": 4, "b": 7})
                print(f"multiply_numbers(4, 7) = {result.content}")
                
                print("\n=== Testing greet_user tool ===")
                result = await mcp_session.call_tool("greet_user", {"name": "Alice"})
                print(f"greet_user('Alice') = {result.content}")
                
                # Test the boto3 tool
                print("\n=== Testing get_aws_region tool (uses boto3) ===")
                result = await mcp_session.call_tool("get_aws_region", {})
                print(f"get_aws_region() = {result.content}")
                
    except Exception as e:
        print(f"Error connecting to MCP server {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_mcp_server())