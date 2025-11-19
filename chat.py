import os
import json
import importlib
import dotenv
from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langchain.tools import tool as lc_tool_decorator

dotenv.load_dotenv()


# ----------------- Tool Utilities -----------------
def load_tools_spec(filepath="tools.json"):
    with open(filepath, "r") as f:
        return json.load(f)


def import_function(import_path: str):
    try:
        module_name, func_name = import_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
        if callable(func):
            return func
    except Exception as e:
        print(f"[WARN] Could not import '{import_path}': {e}")
    return None


def make_decorated_tools(tools_spec):
    tools = []
    for spec in tools_spec:
        func = import_function(spec.get("import_path", ""))
        if func:
            decorated = lc_tool_decorator(
                name_or_callable=spec["name"],
                description=spec.get("description", "")
            )(func)
            tools.append(decorated)
            print(f"[OK] Loaded tool: {spec['name']}")
    return tools


# ----------------- Tool Execution -----------------
def execute_tool_calls(messages, tools):
    for msg in messages:
        for tc in getattr(msg, "tool_calls", []):
            tool_name = tc["name"]
            args = tc.get("args", {})
            func = next((t.func for t in tools if t.name == tool_name), None)
            if func:
                try:
                    tc["result"] = func(**args)
                except Exception as e:
                    tc["result"] = f"Error: {e}"


# ----------------- Agent Utilities -----------------
def create_deepseek_agent(tools=None):
    llm = ChatDeepSeek(api_key=os.getenv("DEEPSEEK_API_KEY"), model="deepseek-chat")
    if tools:
        llm = llm.bind_tools(tools)
    agent = create_agent(
        model=llm,
        system_prompt="You are a helpful assistant. Call tools automatically when needed."
    )
    return agent


def invoke_agent(agent, prompt):
    response = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return response.get("messages", []) if isinstance(response, dict) else response


# ----------------- Serialization -----------------
def serialize(obj):
    if hasattr(obj, "content") and hasattr(obj, "additional_kwargs"):
        result = {
            "type": obj.__class__.__name__,
            "content": obj.content,
            "additional_kwargs": obj.additional_kwargs,
            "response_metadata": getattr(obj, "response_metadata", None),
            "id": getattr(obj, "id", None),
        }
        if hasattr(obj, "tool_calls"):
            result["tool_calls"] = [serialize(tc) for tc in obj.tool_calls]
        return result
    elif isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize(v) for v in obj]
    return obj


# ----------------- Conversation Management -----------------
def handle_user_input(agent, tools, user_input):
    """
    Two-pass process:
    1) Let the agent call tools.
    2) Let the agent formulate final natural response using tool results.
    Returns final user-facing messages (with tool calls attached).
    """
    # First pass: determine tool calls
    first_pass_messages = invoke_agent(agent, user_input)
    execute_tool_calls(first_pass_messages, tools)

    # Prepare tool results summary
    tool_results_summary = ""
    for msg in first_pass_messages:
        for tc in getattr(msg, "tool_calls", []):
            tool_results_summary += f"{tc['name']} returned: {tc['result']}\n"

    # Second pass: agent formulates final response naturally
    final_prompt = (
        f"User asked: {user_input}\n"
        f"Tool results:\n{tool_results_summary}"
        "Please respond naturally to the user."
        "Don't make up the answers yourself, use the results from the tool calls!"
    )
    final_messages = invoke_agent(agent, final_prompt)

    # Attach tool calls to final AI messages for traceability
    for final_msg in final_messages:
        if hasattr(final_msg, "tool_calls"):
            final_msg.tool_calls = []
            for msg in first_pass_messages:
                if hasattr(msg, "tool_calls"):
                    final_msg.tool_calls.extend(msg.tool_calls)

    return final_messages


# ----------------- Main -----------------
def main():
    tools_spec = load_tools_spec()
    tools = make_decorated_tools(tools_spec)

    agent = create_deepseek_agent(tools)

    user_inputs = ["Whats the weather in Cluj-Napoca? and also what is 3 to the power of 6"]
    conversation = []

    for user_input in user_inputs:
        final_messages = handle_user_input(agent, tools, user_input)
        conversation.extend(final_messages)

    serializable_output = [serialize(msg) for msg in conversation]
    with open("agent_output.json", "w") as f:
        json.dump(serializable_output, f, indent=4)

    print("Output saved to agent_output.json")


if __name__ == "__main__":
    main()
