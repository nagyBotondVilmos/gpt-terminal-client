#!/usr/bin/env python3
"""
GPT Terminal Client

Copyright (c) 2025 Botond-Vilmos Nagy
All rights reserved.

This software is provided "as-is", without any express or implied warranty.
You may use, copy, modify, and distribute this software for personal or commercial purposes,
provided that this copyright notice and disclaimer are retained in all copies.

Author: Botond-Vilmos Nagy
Email: nagybotond204@gmail.com
Date: 2025-10-27
"""

import os
import json
import openai
import argparse
import dotenv
from datetime import datetime
from copy import deepcopy

dotenv.load_dotenv()
CONV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations.json")

# ---------- Conversation persistence ----------

def load_conversations():
    if not os.path.exists(CONV_FILE):
        return {
            "active": None,
            "previous_active_list": [],
            "platform": "deepseek",
            "max_tokens": 1024,
            "conversations": {}
        }
    with open(CONV_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Ensure backward compatibility
        data.setdefault("platform", "deepseek")
        data.setdefault("max_tokens", 1024)
        data.setdefault("conversations", {})
        data.setdefault("active", None)
        data.setdefault("previous_active_list", [])
        # Clean previous_active_list of names not in conversations
        data["previous_active_list"] = [
            n for n in data["previous_active_list"] if n in data["conversations"]
        ]
        return data

def save_conversations(data):
    with open(CONV_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def list_conversations(data):
    if not data["conversations"]:
        print("No conversations found.")
        return
    for name, convo in data["conversations"].items():
        mark = " *" if name == data["active"] else ""
        ts = convo.get("created_at", "")
        msg_count = len(convo.get("messages", []))
        print(f"{name}{mark} ({ts}) — {msg_count} messages")

def display_messages(messages):
    print("=" * 50)
    for i, msg in enumerate(messages):
        role = msg["role"].capitalize()
        print(f"{role}: {msg['content']}")
        if i < len(messages) - 1:
            print("-" * 50)
    print("=" * 50)

def show_conversation(data, name):
    convo = data["conversations"].get(name)
    if not convo:
        print(f"No conversation named '{name}'")
        return
    print(f"Conversation: {name}")
    display_messages(convo["messages"])

def delete_conversation(data, name):
    if name not in data["conversations"]:
        print(f"No conversation named '{name}'")
        return

    was_active = data["active"] == name
    del data["conversations"][name]
    
    # Remove all instances of the deleted conversation from the history
    data["previous_active_list"] = [n for n in data["previous_active_list"] if n != name]

    if was_active:
        if data["previous_active_list"]:
            # Set active to the last item in history
            data["active"] = data["previous_active_list"].pop()
            print(f"Deleted '{name}'. Switched to previous conversation '{data['active']}'.")
        else:
            remaining = list(data["conversations"].keys())
            if remaining:
                data["active"] = remaining[0]
                print(f"Deleted '{name}'. Switched to another conversation '{remaining[0]}'.")
            else:
                data["active"] = None
                print(f"Deleted '{name}'. No remaining conversations.")
    else:
        print(f"Deleted conversation '{name}'")

    save_conversations(data)

def clone_conversation(data, source, new_name):
    if source not in data["conversations"]:
        print(f"No conversation named '{source}'")
        return
    if new_name in data["conversations"]:
        print(f"A conversation named '{new_name}' already exists.")
        return
    convo_copy = deepcopy(data["conversations"][source])
    convo_copy["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    data["conversations"][new_name] = convo_copy
    data["active"] = new_name
    save_conversations(data)
    print(f"Created new conversation '{new_name}' from '{source}'")

# ---------- Chat + GPT interaction ----------

##################################################
############# Add new profiles here! #############
##################################################
PROFILES = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
    },
}
##################################################
##################################################
##################################################

def get_client(platform, data):
    previous_platform = data.get("previous_platform")
    if platform not in PROFILES:
        print(f"Error: Unknown platform '{platform}'. Available: {', '.join(PROFILES.keys())}")
        if previous_platform and previous_platform in PROFILES:
            print(f"Reverting to previous platform '{previous_platform}'.")
            data["platform"] = previous_platform
            save_conversations(data)
            platform = previous_platform
        else:
            print("No valid previous platform found. Aborting.")
            exit(1)
    profile = PROFILES[platform]
    api_key = os.getenv(profile["api_key_env"])
    if not api_key:
        print(f"Error: Missing API key for '{platform}' ({profile['api_key_env']}).")
        if previous_platform and previous_platform in PROFILES:
            print(f"Reverting to previous platform '{previous_platform}'.")
            data["platform"] = previous_platform
            save_conversations(data)
            profile = PROFILES[previous_platform]
            api_key = os.getenv(profile["api_key_env"])
            if not api_key:
                print(f"Error: API key for fallback platform '{previous_platform}' also missing. Aborting.")
                exit(1)
        else:
            print("No valid previous platform found. Aborting.")
            exit(1)
    try:
        client = openai.OpenAI(api_key=api_key, base_url=profile["base_url"])
    except Exception as e:
        print(f"Error: Failed to initialize client for platform '{platform}': {e}")
        if previous_platform and previous_platform in PROFILES:
            print(f"Reverting to previous platform '{previous_platform}'.")
            data["platform"] = previous_platform
            save_conversations(data)
            profile = PROFILES[previous_platform]
            api_key = os.getenv(profile["api_key_env"])
            if not api_key:
                print(f"Error: API key for fallback platform '{previous_platform}' also missing. Aborting.")
                exit(1)
            client = openai.OpenAI(api_key=api_key, base_url=profile["base_url"])
        else:
            exit(1)
    data["previous_platform"] = platform
    save_conversations(data)
    return client, profile

def stream_chat(client, convo, model, user_input, max_tokens):
    convo["messages"].append({"role": "user", "content": user_input})
    response = ""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=convo["messages"],
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                print(delta.content, end="", flush=True)
                response += delta.content
        print()
    except KeyboardInterrupt:
        print("\n[Interrupted — partial response saved]")
        if response.strip():
            convo["messages"].append({"role": "assistant", "content": response})
        raise
    else:
        convo["messages"].append({"role": "assistant", "content": response})

def generate_alias(client, model, text):
    prompt = f"Generate a short, descriptive title (3-5 words) for this conversation based on the following text:\n\"{text}\"\nReply with only the title."
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    alias = completion.choices[0].message.content.strip().replace("\n", " ")
    return alias

def interactive_chat(client, model, convo, data, max_tokens, temporary=False):
    active_conversation = data['active'] if not temporary else "new/temporary"
    print(f"Platform: {data['platform']} | Active: {active_conversation} | Max tokens: {data['max_tokens']}")
    print("Type 'exit' or Ctrl+C to quit.\n")

    msg_count = len(convo.get("messages", []))
    if msg_count > 0:
        show_prev = input(f"Do you want to see previous messages ({msg_count})? (Y/n): ").strip().lower()
        if show_prev in ["y", "yes", ""]:
            display_messages(convo["messages"])
        elif show_prev in ["exit", "quit"]:
            print("\nExiting.")
            return

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            print("-" * 50)
            print("Assistant: ", end="", flush=True)
            try:
                stream_chat(client, convo, model, user_input, max_tokens)
                print("-" * 50)
            except KeyboardInterrupt:
                pass
            finally:
                save_conversations(data)
        except KeyboardInterrupt:
            print("\nExiting.")
            break

# ---------- CLI setup ----------

parser = argparse.ArgumentParser(
    description="GPT Terminal Client with persistent, named conversations.",
    epilog="""
Copyright (c) 2025 Botond-Vilmos Nagy
All rights reserved.

Author: Botond-Vilmos Nagy
Email: nagybotond204@gmail.com
"""
)
parser.add_argument("positional_message", nargs="?", help="Message to send (can be used instead of -m)")
parser.add_argument("-p", "--platform", choices=["openai", "deepseek"], help="Platform to use")
parser.add_argument("-m", "--message", help="Message to send (alternative to positional argument)")
parser.add_argument("-mt", "--max-tokens", type=int, dest="max_tokens", help="Max tokens for model output (default 1024)")
parser.add_argument("-c", "--create", nargs="?", const="", metavar="NAME", help="Create a new conversation (optionally provide a name). If no name provided, starts a temporary chat.")
parser.add_argument("--clone", nargs=2, metavar=("NEW_NAME", "SOURCE"), help="Clone an existing conversation")
parser.add_argument("-l", "--list", action="store_true", help="List all conversations")
parser.add_argument("-s", "--select", metavar="NAME", help="Select conversation by name")
parser.add_argument("-w", "--show", metavar="NAME", help="Show a conversation’s messages")
parser.add_argument("-r", "--rename", nargs="+", metavar=("OLD", "NEW"), help="Rename a conversation (or auto-alias if NEW omitted)")
parser.add_argument("-d", "--delete", metavar="NAME", help="Delete a conversation")
parser.add_argument("-i", "--info", action="store_true", help="Show current parameters (platform, active conversation, max tokens, etc.)")
args = parser.parse_args()

# ---------- Main logic ----------

def rename_conversation(data, old_name, new_name, client, model):
    if old_name not in data["conversations"]:
        print(f"No conversation named '{old_name}'")
        return
    if not new_name:
        convo = data["conversations"][old_name]
        if not convo["messages"]:
            print("Cannot generate alias for empty conversation.")
            return
        text_source = convo["messages"][-1]["content"]
        alias = generate_alias(client, model, text_source)
        new_name = alias.replace(" ", "_").lower()
        print(f"Generated alias: {new_name}")
    if new_name in data["conversations"]:
        print(f"A conversation named '{new_name}' already exists.")
        return
    data["conversations"][new_name] = data["conversations"].pop(old_name)
    if data["active"] == old_name:
        data["active"] = new_name
    # Update history list (replace all occurrences)
    data["previous_active_list"] = [new_name if n == old_name else n for n in data["previous_active_list"]]
    save_conversations(data)
    print(f"Renamed '{old_name}' → '{new_name}'")

def main():
    data = load_conversations()
    message = args.message or args.positional_message

    specified_platform = args.platform is not None
    specified_max_tokens = args.max_tokens is not None
    specified_select = args.select is not None
    specified_create = args.create is not None
    specified_clone = args.clone is not None
    specified_list = args.list
    specified_show = args.show is not None
    specified_delete = args.delete is not None
    specified_rename = args.rename is not None
    specified_info = args.info

    action_flags_present = any([
        specified_create, specified_clone, specified_list, specified_show,
        specified_delete, specified_rename, specified_info, message is not None
    ])
    config_flags_present = any([specified_platform, specified_max_tokens, specified_select])

    # ------------------ Configuration-only update ------------------
    if config_flags_present and not action_flags_present:
        if specified_platform:
            if args.platform not in PROFILES:
                print(f"Error: Unknown platform '{args.platform}'. Must be one of: {', '.join(PROFILES.keys())}")
                exit(1)
            data["platform"] = args.platform
            print(f"Platform set to: {args.platform}")
        if specified_max_tokens:
            data["max_tokens"] = args.max_tokens
            print(f"Max tokens set to: {args.max_tokens}")
        if specified_select:
            if args.select not in data["conversations"]:
                print(f"No conversation named '{args.select}' to select.")
            else:
                current_active = data.get("active")
                if current_active and current_active != args.select:
                    data["previous_active_list"].append(current_active)
                data["active"] = args.select
                print(f"Active conversation set to: {args.select}")
        save_conversations(data)
        print("Configuration updated. Exiting.")
        return

    # ------------------ Update configuration for actions ------------------
    if specified_platform:
        if args.platform not in PROFILES:
            print(f"Error: Unknown platform '{args.platform}'. Must be one of: {', '.join(PROFILES.keys())}")
            exit(1)
        data["platform"] = args.platform
    if specified_max_tokens:
        data["max_tokens"] = args.max_tokens
    save_conversations(data)

    platform = data["platform"]
    max_tokens = data.get("max_tokens", 1024)
    client, profile = get_client(platform, data)
    model = profile["model"]

    # ------------------ Actions ------------------
    if args.info:
        active_conv = data.get("active")
        num_convos = len(data.get("conversations", {}))
        print(f"Active conversation: {active_conv}")
        print(f"Platform: {platform}")
        print(f"Max tokens: {max_tokens}")
        print(f"Total conversations: {num_convos}")
        if active_conv and active_conv in data["conversations"]:
            print(f"Messages in active conversation: {len(data['conversations'][active_conv]['messages'])}")
        return

    if args.list:
        list_conversations(data)
        return
    if args.show:
        show_conversation(data, args.show)
        return
    if args.delete:
        delete_conversation(data, args.delete)
        return
    if args.rename:
        old_name = args.rename[0]
        new_name = args.rename[1] if len(args.rename) > 1 else None
        rename_conversation(data, old_name, new_name, client, model)
        return
    if args.clone:
        new_name, source = args.clone
        clone_conversation(data, source, new_name)
        return

    # ------------------ Create conversation (-c) ------------------
    if args.create is not None:
        if args.create == "":
            temp_name = f"temp_{datetime.now().timestamp()}"
            data["conversations"][temp_name] = {"messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
            old_active = data.get("active")
            data["active"] = temp_name
            save_conversations(data)
            print("Starting new temporary conversation. You can set the name after exiting.")
            interactive_chat(client, model, data["conversations"][temp_name], data, max_tokens, True)

            convo = data["conversations"].get(temp_name)
            if not convo or not convo.get("messages"):
                if convo:
                    del data["conversations"][temp_name]
                data["active"] = None
                save_conversations(data)
                print("Temporary conversation discarded (empty).")
                return

            save_choice = input("Do you want to save this conversation? (Y/n): ").strip().lower()
            if save_choice in ["y", "yes", ""]:
                name_input = input("Enter a name for this conversation (leave empty to generate alias): ").strip()
                if name_input:
                    name = name_input
                else:
                    last_text = convo["messages"][-1]["content"] if convo["messages"] else None
                    if not last_text:
                        print("Cannot generate alias for empty conversation.")
                        del data["conversations"][temp_name]
                        data["active"] = None
                        save_conversations(data)
                        print("Temporary conversation discarded.")
                        return
                    name = generate_alias(client, model, last_text)
                    name = name.replace(" ", "_").lower()
                data["conversations"][name] = data["conversations"].pop(temp_name)
                old_active = old_active if old_active != temp_name else None
                if old_active:
                    data["previous_active_list"].append(old_active)
                data["active"] = name
                print(f"Conversation saved as '{name}'")
            else:
                print("Discarding temporary conversation.")
                del data["conversations"][temp_name]
                data["active"] = None
            save_conversations(data)
            return
        else:
            name = args.create
            if name in data["conversations"]:
                print(f"Conversation '{name}' already exists.")
                return
            old_active = data.get("active")
            data["conversations"][name] = {"messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
            data["active"] = name
            if old_active:
                data["previous_active_list"].append(old_active)
            save_conversations(data)
            interactive_chat(client, model, data["conversations"][name], data, max_tokens)
            return

    # ------------------ Select conversation (-s) ------------------
    if args.select:
        if args.select not in data["conversations"]:
            print(f"No conversation named '{args.select}'")
            return
        current_active = data.get("active")
        if current_active and current_active != args.select:
            data["previous_active_list"].append(current_active)
        data["active"] = args.select
        save_conversations(data)

    # ------------------ Send single message ------------------
    if message:
        if args.select:
            convo = data["conversations"][args.select]
        else:
            alias = generate_alias(client, model, message)
            name = alias.replace(" ", "_").lower()
            data["conversations"][name] = {"messages": [], "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
            old_active = data.get("active")
            data["active"] = name
            if old_active:
                data["previous_active_list"].append(old_active)
            convo = data["conversations"][name]
            print(f"Created new conversation '{name}' (alias generated).")
        try:
            stream_chat(client, convo, model, message, max_tokens)
        except KeyboardInterrupt:
            pass
        finally:
            save_conversations(data)
        return

    # ------------------ Interactive mode ------------------
    if not data["active"]:
        print("No active conversation. Use --create or --select to begin. Use -h for help.")
        return
    convo = data["conversations"][data["active"]]
    interactive_chat(client, model, convo, data, max_tokens)

if __name__ == "__main__":
    main()
