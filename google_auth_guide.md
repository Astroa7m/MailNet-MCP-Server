### Guide: How to Get Google Credentials for the MCP Application

This guide will walk you through the necessary steps to authorize the MCP application to access your Gmail account. The process is in two parts:

1. **Part 1: Generating the** `credentials.json` **File**. This is your application's unique ID, which you will get from the Google Cloud Console. You only need to do this once.

2. **Part 2: Configuring the MCP Application.** You will update your configuration file with the path to your `credentials.json` file and specify a location for the `token.json` file to be created.

------------


After configuring, the MCP application itself will handle the final authorization step and the creation of `token.json`.

Prerequisites
* A Google Account (e.g., your personal `@gmail.com` account).
* Access to the JSON configuration file for your MCP application.

------------


##### Part 1: Generating the credentials.json File
Follow these steps to create and download your unique application credentials from Google.

**Step 1: Create a Google Cloud Project**
1. Navigate to the [Google Cloud Console](https://console.cloud.google.com/ "Google Cloud Console") and log in.
2. In the top-left corner, click the project dropdown menu (it may say "Select a project").
3. Click **"NEW PROJECT"**.
4. Enter a **Project name**, for example, "MCP Gmail Access".
5. Click **"CREATE"**.


**Step 2: Enable the Gmail API**
1. You must enable the Gmail API for your new project.
2. Ensure your new project is selected in the top project dropdown.
3. Click the navigation menu (☰) and go to **APIs & Services > Library**.
4. In the search bar, type **"Gmail API"** and select it from the results.
5. Click the blue **"ENABLE"** button and wait for the process to complete.

**Step 3: Configure the OAuth Consent Screen**

This screen is what you will see when you grant permission for the app to access your account.
1. From the navigation menu (☰), go to **APIs & Services > OAuth consent screen**.
2. For "User Type", select **"External"** and click **"CREATE"**.
3. **App Information:**
	* **App name:** Enter a descriptive name like "My Local MCP Client".
	* **User support email:** Select your email address.
	* **Developer contact information:** Enter your email address again.
4. Click **"SAVE AND CONTINUE".**
5. **Scopes:** Now, specify the permissions the app will request.
	* Click **"ADD OR REMOVE SCOPES"**.
	* In the filter, type "Gmail API".
	* For broad access (reading, sending, managing mail), check the box for the scope: `https://www.googleapis.com/auth/gmail.modify.`
	* Click **"UPDATE"**.
6. Click **"SAVE AND CONTINUE"**.
7. **Test Users**: While the app is in "testing" status, only explicitly added users can authorize it.
	* Click **"ADD USERS"**.
	* Enter your own Gmail address (the one you will use with the MCP application).
	* Click **"ADD"**.
8. Click **"SAVE AND CONTINUE**", then review the summary and click **"BACK TO DASHBOARD"**.

**Step 4: Create and Download the Credentials
This is the final step to get your file.**
1. From the navigation menu (☰), go to **APIs & Services > Credentials**.
2. Click **"+ CREATE CREDENTIALS"** at the top of the page and select **"OAuth client ID"**.
3. For **Application type**, choose **"Desktop app"** **( Note that this configuration is for it to be used with desktop client such as Claude or your preferred/custom client.).** 
4. Give it a name, such as "MCP Desktop Credentials".
5. Click **"CREATE".**
6. A pop-up will appear. Click the **"DOWNLOAD JSON"** button.
7. The file will be saved to your computer. It is highly recommended to rename this file to `credentials.json` for clarity.
8. Move this `credentials.json` file to a secure and permanent location on your computer (e.g., `C:\Apps\MCP_Config` or `~/Documents/MCP_Config`). You will need the full path to this file in the next part.

Success! You now have the `credentials.json` file. Do not share it with anyone.

------------



##### Part 2: Configuring the MCP with Your Credentials
Now, you will tell the MCP application where to find your credentials file and where it should save the authorization token.

**Step 1: Get the Full File Paths**

You need to define two file paths:
1. `GOOGLE_CREDENTIALS_FILE_PATH`: This is the full path to the `credentials.json` file you just downloaded and saved.
2. `GOOGLE_PREFERRED_TOKEN_FILE_PATH`: This is the full path where you want the MCP application to **create and store** the `token.json` file. This file does not exist yet. It's best to place it in the same secure folder as your `credentials.json`.

Example:
* If you saved `credentials.json` in `C:\Apps\MCP_Config`, your paths would be:

	* Credentials Path: `C:\Apps\MCP_Config\credentials.json`
	* Token Path: `C:\Apps\MCP_Config\token.json`

**Step 2: Update Your JSON Configuration**

Open the JSON configuration file for your MCP application. Locate the `email_mcp` section and update the `env` object with the file paths you determined in the previous step.

Original Configuration (Locally):

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

**Important:** In JSON strings, you must escape backslashes (\) by using a double backslash (`\\`).

```
"email_mcp": {
    "command": "uv",
    "args": [ "--directory", "PATH\\TO\\MailNet", "run", "-m", "mcp_launcher.server" ],
    "env": {
        "AZURE_APPLICATION_CLIENT_ID": "",
        "AZURE_CLIENT_SECRET_VALUE": "",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "",
        "GOOGLE_CREDENTIALS_FILE_PATH": "C:\\Apps\\MCP_Config\\credentials.json",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "C:\\Apps\\MCP_Config\\token.json"
    }
}
```

**Updated Configuration Example (macOS / Linux):**

Forward slashes (	/	) do not need to be escaped.

```
"email_mcp": {
    "command": "uv",
    "args": [ "--directory", "PATH/TO/MailNet", "run", "-m", "mcp_launcher.server" ],
    "env": {
        "AZURE_APPLICATION_CLIENT_ID": "",
        "AZURE_CLIENT_SECRET_VALUE": "",
        "AZURE_PREFERRED_TOKEN_FILE_PATH": "",
        "GOOGLE_CREDENTIALS_FILE_PATH": "/home/user/Documents/MCP_Config/credentials.json",
        "GOOGLE_PREFERRED_TOKEN_FILE_PATH": "/home/user/Documents/MCP_Config/token.json"
    }
}
```

**Step 3: Run the MCP Application and Authorize**

1. Save your updated JSON configuration file.
2. Run the MCP application as you normally would.
3. The first time you run it after this configuration, the application will:
	* Read your credentials.json.
	* Automatically open a new tab in your web browser.
4. In the browser:
	* Choose the Google Account you added as a "Test User".
	* You will see a warning screen: "Google hasn’t verified this app". This is expected. Click "Advanced" and then click "Go to [your app name] (unsafe)".
	* Grant the requested permissions by clicking "Allow".
	* The browser tab will show a success message and can be closed.
5. The MCP application will now proceed. It has successfully used your permission to create the `token.json` file in the location you specified.

You will not have to repeat the browser authorization step on subsequent runs, as the application will reuse the generated token.json.

#### For more information, check [Gmail API Documentation](https://developers.google.com/workspace/gmail/api/guides)
#### Check [Azure Authorization Guide](www.link.to.azure.auth.guide.com) if you haven't 