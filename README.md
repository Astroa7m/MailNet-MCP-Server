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

#### Acquiring Azure Token (Personal local use)
1. Go to `email_client/outlook_helpers.py`.
2. run the file (by default runs `acquiring_azure_token_for_personal_use` function.
To acquire `client_id` & `client_secret` Please check [Azure Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/azure_auth_guide.md)
And make sure to add them to your env vars with the names shown below.
```
def acquiring_azure_token_for_personal_use():
    load_dotenv()
    client_id = os.getenv("AZURE_APPLICATION_CLIENT_ID")
    client_secret = os.getenv("AZURE_SECRET_VALUE")
    OutlookClient(client_id=client_id, client_secret=client_secret,
                                 redirect_uri="http://localhost:3000/callback")
```
It will do the following:
- launch the browser and prompt you to sign in to your outlook account.
- After successful login and approval of permissions, it will redirect you to `http://localhost:3000/callback` unless you specified different url in the constructor via `redirect_uri` param.
- Copy the code after `code=` and before `&client_info` within the browser url and paste it in the terminal where you launched the file.
- Done now you will have your azure token under `email_client` named `azure_token.json` by default (can be changed via `token_file_name` param in `OutlookClient` constructor).
3. Provide that path to `AZURE_PREFERRED_TOKEN_FILE_PATH` env variable and you are good to go.
---

#### Acquiring Google Token (Personal local use)
1. Go to `email_client/gmail_helpers.py`.
2. run the file (by default runs `acquiring_google_token_for_personal_use` function.
To acquire `google_credentials_file` Please check [Google Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/google_auth_guide.md) 
And make sure to add the path to it in your env vars with the name shown below.
```
def acquiring_google_token_for_personal_use():
    load_dotenv()
    google_credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE_PATH")
    GmailClient(credential_file=google_credentials_file)
```
It will do the following:
- launch the browser and prompt you to sign in to your gmail account.
- After successful login and approval of permissions, it will redirect you to a window with a message `The authentication flow has completed. You may close this window.` that means you are done here.
- Done now you will have your google token under `email_client` named `google_token.json` by default (can be changed via `token_file_name` param in `GmailClient` constructor).
3. Provide that path to `GOOGLE_CREDENTIALS_FILE_PATH` env variable and you are good to go.
---

## 🔒 Environment Variables

Check the [Azure Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/azure_auth_guide.md) and [Google Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/google_auth_guide.md) to learn how to set up both accounts and get your credentials ready.

Set your environment variables for provider credentials:

#### Gmail
**GOOGLE_CREDENTIALS_FILE_PATH**=path/to/google_credentials.json  
**GOOGLE_PREFERRED_TOKEN_FILE_PATH**=path/to/google_token.json  

#### Outlook (Azure)
**AZURE_APPLICATION_CLIENT_ID**=your-client-id  
**AZURE_CLIENT_SECRET_VALUE**=your-secret  
**AZURE_PREFERRED_TOKEN_FILE_PATH**=path/to/azure_token.json  

#### Other (Important for local use)
The following env variable is important to be set when running it locally or for Claude Desktop. The value deosn't matter but as long as the field is there you will be able to run it locally.
It was introduced to make the server flexible to be run over http/s or stdio and to route the server to either look for credentials in local files or expect it from the client via http/s headers.

**is_local**="true"

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
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "C:\\Path\\To\\google_token.json",
        "is_local": "true"
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
