# Guide: How to Get Azure Credentials for the MCP Application

This guide will walk you through the necessary steps to authorize the MCP application to access your Microsoft account data (like Outlook emails) via the Microsoft Graph API. The process is in two parts:
1. **Part 1: Generating App Credentials in Azure**. You will register an application in the Microsoft Azure portal to get an **Application (client) ID** and a **Client Secret**. These are the application's unique identifiers.
2. **Part 2: Configuring the MCP Application.** You will update your configuration file with the credentials you generated and specify a location for the authorization token file to be created.

------------

After configuration, the MCP application will handle the user login, consent, and the creation of the token file.

**Prerequisites**
* A Microsoft Account (this can be a personal `@outlook.com`/`@hotmail.com` account or a work/school Microsoft 365 account).
* Access to the JSON configuration file for your MCP application.

------------


#### Part 1: Generating Application Credentials in Azure
Follow these steps to create and configure your application in the Azure portal.

	Note: Microsoft's identity platform is now called "Microsoft Entra ID", which was formerly known as Azure Active Directory (Azure AD).

**Step 1: Navigate to the Azure Portal and Register an Application**
1. Go to the [Microsoft Azure Portal](https://portal.azure.com/auth/login/ "Microsoft Azure Portal") and sign in with your Microsoft account.
2. In the search bar at the top, search for and select **"Microsoft Entra ID"**.
3. In the left-hand menu of the Microsoft Entra ID page, select **"App registrations**".
4. Click on **"+ New registration"**.

**Step 2: Configure the New Application**
1. Name: Give your application a descriptive name, such as "My MCP Outlook Client".
2.** Supported account types: **This is a crucial setting. For the most flexibility, select **"Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)"**.
3. Redirect URI (optional but recommended):
	* Select **"Web"** from the dropdown.
	* Enter `http://localhost:3000/callback` (Note it should be exactly the same, if you want to change it to a different url, modify [mcp-server/api/main.py](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/api/main.py "mcp-server/api/main.py")) in the URL field. Your MCP application will use this to capture the authorization response after you log in.
4. Click the **"Register"** button at the bottom.

**Step 3: Get the Application (client) ID**

After the application is created, you will be taken to its "Overview" page.
1. Look for the **"Application (client) ID"** field.
2. Click the copy icon next to the ID to copy it to your clipboard.
3. **Save this value** in a temporary text file. You will need it for Part 2.

**Step 4: Create a Client Secret**

A client secret is essentially the application's password.
1. In the left-hand menu for your app registration, click on **"Certificates & secrets"**.
2. Under the "Client secrets" section, click **"+ New client secret"**.
3. Add a **Description** (e.g., "MCP Secret Key").
4. Choose an **Expires** duration. A duration of 6 or 12 months is common for personal projects.
5. Click **"Add"**.

	**IMPORTANT: COPY THE SECRET VALUE IMMEDIATELY**

	A secret will be generated and displayed. You must copy the **Value** of the secret now. This value will be hidden forever after you leave this page.
6. Click the copy icon next to the secret's **Value**.
7.  **Save this value** in your temporary text file along with your Client ID.

**Step 5: Configure API Permissions**

Now, you must specify what permissions your application needs. For accessing email, you'll need the `Mail.ReadWrite` permission.
1. In the left-hand menu for your app registration, click on **"API permissions"**.
2. Click on "+ Add a permission".
3. Select **"Microsoft Graph"** from the list of common Microsoft APIs.
4. Choose **"Delegated permissions"**. This means the application will access the API on behalf of the signed-in user.
5. In the "Select permissions" search box, type **"Mail"**.
6. Expand the "Mail" section and check the box for `Mail.ReadWrite`. This allows the app to read, create, update, and delete emails.
7. Click the **"Add permissions"** button at the bottom.

**Success!** You have now collected the two critical pieces of information: the **Application (client) ID** and the **Client Secret Value**.

------------


#### Part 2: Configuring the MCP with Your Azure Credentials
Now, you will provide the credentials you just generated to the MCP application via its JSON configuration file.

**Step 1: Define Your Credentials and Token Path**
1. `AZURE_APPLICATION_CLIENT_ID`: This is the "Application (client) ID" you copied in Step 3.
2. `AZURE_CLIENT_SECRET_VALUE`: This is the secret "Value" you copied in Step 4.
   3. `AZURE_PREFERRED_TOKEN_FILE_PATH`: This is the full path where you want the MCP application to create and store the authorization token file (e.g., `azure_token.json`). This file does not exist yet. It's best to use a separate file from your Google token.

**Example:**
If you want to store the token in `C:\Apps\MCP_Config`, your path would be: `C:\Apps\MCP_Config\azure_token.json`

**Step 2: Update Your JSON Configuration**

Open your MCP application's JSON configuration file and locate the `email_mcp` section to update the `env` object.

**Original Configuration:**

```
"email_mcp": {
    "command": "uv",
    "args": [ "--directory", "PATH\\TO\\MailNet", "run", "-m", "mcp_launcher.server" ],
    "env": {
        "AZURE_APPLICATION_CLIENT_ID": "",
        "AZURE_CLIENT_SECRET_VALUE": "",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "",
        "GOOGLE_CREDENTIALS_FILE_PATH": "",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": ""
    }
}
```
**Updated Configuration Example (Windows):**

Remember: In JSON strings, you must escape backslashes (\) by using a double backslash (`\\`).


```
"email_mcp": {
    "command": "uv",
    "args": [ "--directory", "PATH\\TO\\MailNet", "run", "-m", "mcp_launcher.server" ],
    "env": {
        "AZURE_APPLICATION_CLIENT_ID": "ab1234cd-e567-890f-gh12-ijklmn345opq",
        "AZURE_CLIENT_SECRET_VALUE": "aBcDe~FGHijk_lmnOP.qrstuv-wxYZ12345678",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "C:\\Apps\\MCP_Config\\azure_token.json",
        "GOOGLE_CREDENTIALS_FILE_PATH": "C:\\Apps\\MCP_Config\\credentials.json",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "C:\\Apps\\MCP_Config\\token.json"
    }
}
```
**Updated Configuration Example (macOS / Linux):**
Forward slashes (/) do not need to be escaped.

```
"email_mcp": {
    "command": "uv",
    "args": [ "--directory", "PATH/TO/MailNet", "run", "-m", "mcp_launcher.server" ],
    "env": {
        "AZURE_APPLICATION_CLIENT_ID": "ab1234cd-e567-890f-gh12-ijklmn345opq",
        "AZURE_CLIENT_SECRET_VALUE": "aBcDe~FGHijk_lmnOP.qrstuv-wxYZ12345678",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "/home/user/mcp_config/azure_token.json",
        "GOOGLE_CREDENTIALS_FILE_PATH": "/home/user/mcp_config/credentials.json",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "/home/user/mcp_config/token.json"
    }
}
```
**Step 3: Run the MCP Application and Authorize**
1. Save your updated JSON configuration file.
2. Run the MCP application.
3. The first time you run it, the application will:
	* Read your Azure client ID and secret.
	* **Automatically open a new tab in your web browser** for Microsoft login.
4. In the browser:
	* Sign in with your Microsoft account.
	* A "**Permissions requested"** consent screen will appear, showing the permissions you configured (e.g., "Read, compose, and send mail").
	* Click **"Accept"** to grant permission to the application.
	* You may be redirected to the `localhost` address you specified, and the page might say "This site can’t be reached." This is normal. You can safely close the browser tab.
5. The MCP application will now proceed. It has successfully obtained an authorization token and saved it to the file path you specified in `AZURE_PREFERRED_TOKEN_FILE_PATH`.

You are now fully configured. The application will reuse the saved token for future runs without requiring you to log in again.

#### For more information, check [Azure Service Documentation](https://learn.microsoft.com/en-us/azure/app-service/overview-authentication-authorization)
#### Check [Google Authorization Guide](https://github.com/Astroa7m/MailNet-MCP-Server/blob/main/google_auth_guide.md) if you haven't 