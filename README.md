# MCP Server on Amazon Bedrock AgentCore with IAM Authentication

This guide demonstrates how to deploy a Model Context Protocol (MCP) server to Amazon Bedrock AgentCore Runtime using IAM authentication instead of OAuth/Cognito tokens.

## Prerequisites

- Python 3.10 or higher
- AWS account with appropriate permissions
- AWS CLI configured with admin credentials

## Project Structure

```
bedrock_agentcore_iam_runtime_mcp_server/
├── my_iam_mcp_server.py    # MCP server implementation
├── requirements.txt        # Python dependencies
├── test_mcp_client.py     # Test client
├── mcp-access-policy.json # IAM policy for MCP access
└── README.md              # This file
```

**Note**: If you're cloning this repository, you can skip to Step 3 as the files are already created.

## Step 1: Create Your MCP Server

Create `my_iam_mcp_server.py`:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

@mcp.tool()
def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers together"""
    return a * b

@mcp.tool()
def greet_user(name: str) -> str:
    """Greet a user by name"""
    return f"Hello, {name}! Nice to meet you."

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

## Step 2: Create Requirements File

Create `requirements.txt`:

```
mcp
boto3
bedrock-agentcore
bedrock-agentcore-starter-toolkit
run-mcp-servers-with-aws-lambda
```

## Step 3: Configure and Deploy

Configure your MCP server:

```bash
agentcore configure -e my_iam_mcp_server.py --protocol MCP
```

During configuration:
- **Execution Role**: Press Enter to auto-create
- **ECR Repository**: Press Enter to auto-create  
- **Dependency file**: Press Enter to use detected `requirements.txt`
- **Authorization**: Choose `no` for OAuth (uses IAM by default)

Deploy to AWS:

```bash
agentcore launch
```

After successful deployment, you'll receive an Agent ARN like:
```
arn:aws:bedrock-agentcore:<aws-region>:<account-id>:runtime/my_iam_mcp_server-<random-id>
```

**Save this ARN - you'll need it in the next step.**

## Step 4: Test with Your Current Credentials

Create `test_mcp_client.py`:

```python
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

    async with streamablehttp_client_with_sigv4(
        url=mcp_url,
        service="bedrock-agentcore",
        region="<aws-region>",
        credentials=credentials,
        timeout=120,
        terminate_on_close=False
    ) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()
            
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

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
```

**Before running, update the following placeholders in `test_mcp_client.py`:**
- Replace `<aws-region>` with your AWS region (e.g., `us-east-1`)
- Replace `<account-id>` with your AWS account ID
- Replace `<random-id>` with the random ID from your Agent ARN

Test with your current credentials:

```bash
python3 test_mcp_client.py
```

## Step 5: Create Separate IAM User for Testing

### Create IAM User

```bash
# Create the IAM user
aws iam create-user --user-name mcp-test-user

# Create access keys for the user
aws iam create-access-key --user-name mcp-test-user
```

Save the `AccessKeyId` and `SecretAccessKey` from the output.

### Create IAM Policy

Create `mcp-access-policy.json`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": "arn:aws:bedrock-agentcore:<aws-region>:<account-id>:runtime/my_iam_mcp_server-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:InvokeAgentRuntime"
            ],
            "Resource": "arn:aws:bedrock-agentcore:<aws-region>:<account-id>:runtime/*"
        }
    ]
}
```

**Before creating the policy, update the following placeholders in `mcp-access-policy.json`:**
- Replace `<aws-region>` with your AWS region (e.g., `us-east-1`)
- Replace `<account-id>` with your AWS account ID

Create and attach the policy:

```bash
# Create the policy
aws iam create-policy \
    --policy-name MCPServerAccessPolicy \
    --policy-document file://mcp-access-policy.json

# Attach the policy to the user (replace <account-id> with your AWS account ID)
aws iam attach-user-policy \
    --user-name mcp-test-user \
    --policy-arn arn:aws:iam::<account-id>:policy/MCPServerAccessPolicy
```

**Before running the attach command, replace `<account-id>` with your AWS account ID.**

### Test with New IAM User

Open a new terminal to not use your Admin Credentials and set your environment variables with the new user's credentials:

```bash
export AWS_ACCESS_KEY_ID="<access-key-id>"
export AWS_SECRET_ACCESS_KEY="<secret-access-key>"
export AWS_DEFAULT_REGION="<aws-region>"

# Run the test
python3 test_mcp_client.py
```

**Before running, replace the following:**
- `<access-key-id>` with the AccessKeyId from the create-access-key command
- `<secret-access-key>` with the SecretAccessKey from the create-access-key command
- `<aws-region>` with your AWS region (e.g., `us-east-1`)

## Expected Output

```
Connecting to: https://bedrock-agentcore.<aws-region>.amazonaws.com/runtimes/arn%3Aaws%3Abedrock-agentcore%3A<aws-region>%3A<account-id>%3Aruntime%2Fmy_iam_mcp_server-<random-id>/invocations?qualifier=DEFAULT

=== Available Tools ===
  - add_numbers: Add two numbers together
  - multiply_numbers: Multiply two numbers together
  - greet_user: Greet a user by name

=== Testing add_numbers tool ===
add_numbers(5, 3) = [TextContent(type='text', text='8', annotations=None, meta=None)]

=== Testing multiply_numbers tool ===
multiply_numbers(4, 7) = [TextContent(type='text', text='28', annotations=None, meta=None)]

=== Testing greet_user tool ===
greet_user('Alice') = [TextContent(type='text', text='Hello, Alice! Nice to meet you.', annotations=None, meta=None)]
```

## Key Benefits

- No OAuth/Cognito setup required - Uses standard AWS IAM authentication
- SigV4 signing - Automatic AWS request signing with boto3 credentials

## References

- [AWS Bedrock AgentCore MCP Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html)
- [AWS Bedrock AgentCore MCP Server Tutorial](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/01-AgentCore-runtime/02-hosting-MCP-server/hosting_mcp_server.ipynb)
