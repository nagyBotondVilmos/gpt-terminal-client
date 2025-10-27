# GPT Terminal Client

A lightweight terminal-based chat client for GPT-powered platforms (OpenAI or Deepseek) with **persistent, named conversations**, history tracking, and interactive chat streaming. Perfect for managing multiple GPT conversations directly from your terminal.

## Features

* Create, delete, rename, and clone conversations.
* Maintain a **history stack** to track previously active conversations.
* Generate conversation aliases automatically.
* Stream GPT responses in real-time.
* Supports multiple platforms (OpenAI GPT and Deepseek).
* Platform expnsion possible, as long as it's compatible with "openai" library.
* Configurable maximum token limit per conversation.

---

## Installation

1. **Clone the repository**

```bash
git clone https://github.com/nagyBotondVilmos/gpt-terminal-client.git
cd gpt-terminal-client
```

2. **Create a Python virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set API keys** in a `.env` file in the project root (one profile required to work only):

```
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```

5. **Make the script executable (optional)**

```bash
chmod +x chat.py
```

---

## Usage

Start a new temporary conversation:

```bash
./chat.py --create
```

Create a named conversation:

```bash
./chat.py --create "my_conversation"
```

Send a single message without interactive mode (alias generated automatically if no conversation exists):

```bash
./chat.py "Hello, GPT!"
```

Select an existing conversation:

```bash
./chat.py --select my_conversation
```

List all conversations:

```bash
./chat.py --list
```

Show conversation messages:

```bash
./chat.py --show my_conversation
```

Rename a conversation:

```bash
./chat.py --rename old_name new_name
```

Delete a conversation:

```bash
./chat.py --delete my_conversation
```

Clone a conversation:

```bash
./chat.py --clone new_name source_name
```

Show current configuration:

```bash
./chat.py --info
```

Set platform or max tokens without starting a conversation:

```bash
./chat.py --platform openai --max-tokens 1500
```

---

## Notes

* The script automatically maintains a **previously active conversation stack**, allowing seamless switching when conversations are deleted or renamed.
* Temporary conversations can be discarded or saved with a custom or AI-generated name.
* Supports streaming partial responses for faster feedback in the terminal.
