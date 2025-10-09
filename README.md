# 📬 MailNet MCP Server

MailNet Server is a unified, agentic email orchestration server built for the [Model Context Protocol](https://github.com/modelcontextprotocol/servers). It supports Gmail and Outlook with standardized metadata, secure credential injection, and a rich toolset for assistant-driven workflows. It is the MCP server that powers [MailNet](https://github.com/Astroa7m/MailNet) Mailing Agentic AI.

---

## 🚀 Features

- ✅ Unified Gmail + Outlook abstraction
- ✅ Automatic token refresh and credential hygiene
- ✅ Standardized base class for provider extension
- ✅ Agentic email settings endpoint (tone, signature, thread context, etc.)
- ✅ Modular toolset: send, read, search, label, archive, reply, delete, draft

---

## 🛠 Installation

### 1. Manual Clone & Launch

```bash
git clone https://github.com/Astroa7m/MailNet-MCP-Server.git
cd MailNet-MCP-Server
```

#### Install requirements

`pip install -r requirements.txt`

Note if you are going to use `uv` for launching you should first install it via:

`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

#### Launch
Either with uv via:

`uv run -m mcp_launcher.server`

or

`python -m mcp_launcher.server`

---

## 🔒 Environment Variables

Set your environment variables for provider credentials:

#### Gmail
**GOOGLE_CREDENTIALS_FILE_PATH**=path/to/google_credentials.json  
**GOOGLE_PREFERRED_TOKEN_FILE_PATH**=path/to/google_token.json  

#### Outlook (Azure)
**AZURE_APPLICATION_CLIENT_ID**=your-client-id  
**AZURE_CLIENT_SECRET_VALUE**=your-secret  
**AZURE_PREFERRED_TOKEN_FILE_PATH**=path/to/azure_token.json  

Check the [Azure Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/azure_auth_guide.md) and [Google Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/google_auth_guide.md) to learn how to set up both accounts and get your tokens/credentials ready.

---

## 🖥 Claude Desktop Integration

Add the following to your `claude_desktop_config.json`:

```
{
  "mcpservers": {
    "email_mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Path\\To\\mcp-server",
        "run",
        "-m",
        "mcp_launcher.server"
      ],
      "env": {
        "AZURE_APPLICATION_CLIENT_ID": "<AZURE_APPLICATION_CLIENT_ID>",
        "AZURE_CLIENT_SECRET_VALUE": "<AZURE_CLIENT_SECRET_VALUE>",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "C:\\Path\\To\\azure_token.json",
        "GOOGLE_CREDENTIALS_FILE_PATH": "C:\\Path\\To\\google_credentials.json",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "C:\\Path\\To\\google_token.json"
      }
    }
  }
}
```
---

## 🧠 Agentic Email Settings

You can view settings via the `load_email_settings` tool or update them via the `update_email_settings` tool.
```
{
  "language": "en",
  "tone": "formal",
  "writing_style": "clear_and_concise",
  "sender_name": "Ahmed Samir",
  "organization_name": "Kalima Tech",
  "include_signature": true,
  "signature": "Best regards,\n{{sender_name}}\n{{organization_name}}",
  "preferred_greeting": "Dear {{recipient_name}},",
  "auto_adjust_tone": true,
  "include_thread_context": true,
  "character_limit": 1000,
  "prompt_prefix": "You are an AI email assistant for {{organization_name}}. Keep messages professional, polite, and to the point.",
  "default_provider": "google"
}
```
---

## 📦 Tools Supported

| Tool                  | Description                       |
|-----------------------|-----------------------------------|
| send_email            | Compose and send messages         |
| read_email            | Fetch and inspect messages        |
| create_draft          | Prepare messages                  |
| send_draft            | Finalize and send                 |
| search_email          | Query inbox with semantic filters |
| toggle_label          | Modify categories/labels          |
| archive_email         | Clean up inbox                    |
| reply_email           | Respond in thread context         |
| delete_email          | Remove messages                   |
| load_email_settings   | View current email settings       |
| update_email_settings | Update runtime email settings     |

---

## 🤝 Contributing

MailNet server is modular and extensible. To add a new provider, subclass the base client and implement the predefined hooks. PRs welcome!
