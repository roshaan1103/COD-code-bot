# COD Live Code Monitor

A Python-based Twitch giveaway code monitoring bot that detects eligible game redemption codes in Twitch chat, filters messages by sender permissions, identifies the intended gaming platform, prevents duplicate processing, and routes detected codes to the appropriate redemption adapter.

The project currently supports **Steam and Battle.net redemption adapters**, with a dry-run mode for safe testing. It uses Twitch OAuth for authentication and Twitch IRC over WebSocket to receive live chat messages.

> **Important:** Keep `dry_run=True` during development and testing. Real redemption should only be enabled deliberately when you understand the consequences. Never test with real giveaway codes unless you intend to redeem them.

---

## Table of Contents

* [Features](#features)
* [How It Works](#how-it-works)
* [Technology Stack](#technology-stack)
* [Requirements](#requirements)
* [Installation](#installation)

  * [Option 1: Download from GitHub](#option-1-download-from-github)
  * [Option 2: Clone the Repository](#option-2-clone-the-repository)
  * [Create a Virtual Environment](#create-a-virtual-environment)
  * [Install Dependencies](#install-dependencies)
* [Configuration](#configuration)
* [Twitch Authentication](#twitch-authentication)
* [Running the Bot](#running-the-bot)
* [Supported Platforms and Code Detection](#supported-platforms-and-code-detection)
* [Message Filtering and Duplicate Prevention](#message-filtering-and-duplicate-prevention)
* [Dry-Run and Real Redemption](#dry-run-and-real-redemption)
* [Testing](#testing)
* [Project Structure](#project-structure)
* [Using This Project on Another Computer](#using-this-project-on-another-computer)
* [Troubleshooting](#troubleshooting)
* [Security Recommendations](#security-recommendations)
* [Current Limitations](#current-limitations)
* [Future Improvements](#future-improvements)
* [License](#license)

---

## Features

### Twitch Chat Monitoring

* Connects to Twitch chat using IRC over WebSocket.
* Monitors one or more configured Twitch channels.
* Receives live chat messages.
* Processes messages through a structured message-handling pipeline.

### Authorized Sender Filtering

The bot only processes giveaway codes from eligible senders.

A message is considered authorized when the sender is:

* The broadcaster of the channel, or
* A moderator of the channel.

Codes posted by ordinary viewers are rejected by the message handler.

This reduces the likelihood of processing fake, misleading, or unauthorized codes.

### Platform Identification

The bot looks for explicit platform labels before extracting a code.

Examples of recognized platform labels include:

* Steam
* Battle.net
* Battle Net
* BattleNet
* BNet
* BN
* Xbox
* PlayStation

The detector is case-insensitive.

For example, a message might contain:

`Steam: EXAMPLE-CODE-123`

The bot identifies the platform and extracts the candidate code.

**The example above is illustrative, not a real redemption code.**

### Multiple Codes in One Message

The code detector can identify multiple platform/code pairs in a single message.

For example:

`Steam: EXAMPLE-STEAM-CODE BN: EXAMPLE-BNET-CODE`

Each detected pair can be handled as a separate redemption job.

The examples in this README are placeholders. They must not be submitted to real redemption websites.

### Duplicate Prevention

The bot maintains a cache of recently processed codes to avoid repeatedly queuing the same code.

The current deduplication behavior:

* Uses the code itself as the deduplication key.
* Retains entries for approximately five minutes.
* Limits the cache to 1,000 entries.
* Prevents a repeated code from being queued while its cache entry remains active.

The current implementation does not use the platform as part of the deduplication key. Therefore, the same code detected for different platforms may be treated as a duplicate.

### Redemption Queue and Worker

Detected codes are converted into redemption jobs and added to a queue.

A worker retrieves queued jobs and sends them to the appropriate platform adapter.

This separates chat monitoring from redemption processing and provides a foundation for supporting additional platforms later.

### Steam and Battle.net Adapters

The project contains dedicated redemption adapters for:

* Steam
* Battle.net

The adapters are responsible for platform-specific redemption behavior.

A browser manager provides browser automation functionality, while the worker coordinates job processing.

The adapters support dry-run testing so the workflow can be tested without submitting actual codes.

### Local Twitch OAuth Authentication

The project implements Twitch OAuth authorization.

The authentication process:

1. Generates a random OAuth state value.
2. Starts a local callback server on port `3000`.
3. Opens the Twitch authorization page in the browser.
4. Receives the authorization code.
5. Verifies the returned OAuth state.
6. Exchanges the authorization code for access and refresh tokens.
7. Validates the access token.
8. Saves the token information locally.

The resulting `twitch_tokens.json` file is sensitive and must never be published to GitHub.

---

## How It Works

The general processing pipeline is:

```text
Twitch Channel
      |
      v
Twitch IRC WebSocket Connection
      |
      v
Receive Chat Message
      |
      v
Normalize Message
      |
      v
Check Sender Authorization
      |
      v
Detect Explicit Platform Labels
      |
      v
Extract Candidate Codes
      |
      v
Check Duplicate Cache
      |
      v
Create Redemption Jobs
      |
      v
Add Jobs to Queue
      |
      v
Redemption Worker
      |
      +---------------------+
      |                     |
      v                     v
 Steam Adapter        Battle.net Adapter
      |                     |
      v                     v
 Dry Run or           Dry Run or
 Redemption           Redemption
```

The pipeline is designed to keep responsibilities separate.

* **IRC receiver:** receives Twitch chat messages.
* **Message handler:** checks sender permissions and coordinates detection and queuing.
* **Code detector:** identifies platform labels and extracts candidate codes.
* **Deduplicator:** blocks recently processed codes.
* **Redemption queue:** stores pending jobs.
* **Worker:** retrieves jobs and invokes the appropriate adapter.
* **Platform adapters:** handle platform-specific redemption logic.
* **Browser manager:** manages browser automation resources.

The exact behavior of an individual adapter depends on its implementation and the platform's current redemption flow.

---

## Technology Stack

| Technology                      | Purpose                                   |
| ------------------------------- | ----------------------------------------- |
| Python                          | Main programming language                 |
| Twitch OAuth                    | Twitch account authorization              |
| Twitch IRC over WebSocket       | Live Twitch chat messages                 |
| `httpx`                         | HTTP requests for OAuth operations        |
| `python-dotenv`                 | Load configuration from `.env`            |
| Python `asyncio`                | Asynchronous processing where implemented |
| Python queues                   | Coordinate redemption jobs                |
| Playwright                      | Browser automation                        |
| `pytest` or Python test scripts | Test project components                   |

The installed dependencies are defined in `requirements.txt`.

---

## Requirements

Before installing the project, ensure you have:

* Windows, Linux, or another supported Python environment.
* Python 3.11 or another version compatible with the project's dependencies.
* Git, if you want to clone the repository.
* A Twitch account.
* A Twitch Developer Application.
* A web browser for Twitch authorization.
* An internet connection.
* Enough disk space for the Python environment and browser binaries.

The commands in this README use Windows PowerShell. Linux and macOS users may need to adapt the virtual environment activation and other operating-system-specific commands.

---

## Installation

There are two ways to obtain the project.

### Option 1: Download from GitHub

This is the easiest option for users who do not want to use Git commands.

1. Open the project's GitHub repository.
2. Select **Code**.
3. Select **Download ZIP**.
4. Extract the ZIP file to a convenient directory.

For example:

```text
L:\COD-code-bot
```

The extracted project should contain `app`, `requirements.txt`, and the other tracked project files.

> GitHub does not include files excluded by `.gitignore`. Users must create their own `.env` file, authenticate their own Twitch account, and generate their own `twitch_tokens.json`.

### Option 2: Clone the Repository

If Git is installed, open PowerShell and run:

```powershell
git clone YOUR_REPOSITORY_URL
```

Replace `YOUR_REPOSITORY_URL` with the actual URL of the repository.

Then enter the project directory:

```powershell
cd COD-code-bot
```

Do not copy a placeholder repository URL literally.

### Create a Virtual Environment

From the project root, create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

After activation, your terminal prompt should begin with something similar to:

```text
(.venv) PS L:\COD-code-bot>
```

If PowerShell blocks activation because of the execution policy, you can use this alternative for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

This changes the execution policy only for the current PowerShell process.

### Install Dependencies

With the virtual environment activated, upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project dependencies:

```powershell
python -m pip install -r requirements.txt
```

The installation may take some time depending on the packages and your internet connection.

### Install Playwright Browser Components

The project uses Playwright for browser automation.

Install the required browser binaries with:

```powershell
python -m playwright install
```

This installs the browsers supported by the installed Playwright version.

If your project configuration or browser manager explicitly requires a particular browser, install that browser instead. For example:

```powershell
python -m playwright install chromium
```

Do not run both commands unnecessarily; use the one appropriate for your implementation.

---

## Configuration

The bot reads its configuration from a `.env` file in the project root.

Create a new file named:

```text
.env
```

It should be located alongside `requirements.txt`, not inside the `app` directory.

### Required `.env` Variables

The configuration module expects the following variables:

```dotenv
TWITCH_CLIENT_ID=YOUR_TWITCH_CLIENT_ID
TWITCH_CLIENT_SECRET=YOUR_TWITCH_CLIENT_SECRET
TWITCH_REDIRECT_URI=http://localhost:3000
TWITCH_CHANNELS=your_channel_name
```

Replace every placeholder with your own values.

**Do not include quotation marks around the values unless your configuration specifically requires them. Do not share or commit your Client Secret.**

#### `TWITCH_CLIENT_ID`

The Client ID of your own Twitch Developer Application.

#### `TWITCH_CLIENT_SECRET`

The Client Secret associated with that application.

Keep it private. Anyone who obtains it may be able to misuse your application credentials.

#### `TWITCH_REDIRECT_URI`

The redirect URL configured in your Twitch Developer Application.

The default used by the project is:

```text
http://localhost:3000
```

The redirect URL configured in Twitch and the value in `.env` must match.

The local OAuth callback server listens on port `3000`, so ensure that port is available during authentication.

#### `TWITCH_CHANNELS`

A comma-separated list of Twitch channel logins to monitor.

For example:

```dotenv
TWITCH_CHANNELS=channel_one,channel_two
```

Replace the example channel names with the actual Twitch channel logins.

The configuration module:

* Removes leading and trailing whitespace.
* Removes a leading `@`.
* Converts channel names to lowercase.
* Removes duplicate entries while preserving their order.

For example, entries such as `@ExampleChannel` and `examplechannel` are normalized to the same channel login.

Use channel login names, not display names or channel URLs.

### Configuration Validation

When the configuration module loads, it checks that:

* `TWITCH_CLIENT_ID` is present.
* `TWITCH_CLIENT_SECRET` is present.
* At least one channel is configured.

If a required value is missing, the application raises an error explaining which configuration value needs attention.

### Never Commit `.env`

The `.env` file contains sensitive credentials.

It is excluded by the project's `.gitignore` and should remain local to each installation.

Users should create their own `.env` file rather than copying another person's credentials.

---

## Twitch Authentication

Each user must authorize their own Twitch account.

Do not use another person's Client Secret or `twitch_tokens.json`.

### Step 1: Create a Twitch Developer Application

Open the official Twitch Developer Console:

**https://dev.twitch.tv/console/apps**

Sign in to your Twitch account and register an application.

Use the OAuth redirect URL:

```text
http://localhost:3000
```

This must match the `TWITCH_REDIRECT_URI` configured in your `.env` file.

Choose the application category and settings appropriate for your application.

After creating the application, copy its Client ID and Client Secret into your local `.env` file.

Keep the Client Secret private.

### Step 2: Start Authentication

Open PowerShell in the project root.

Activate the virtual environment if it is not already active:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run:

```powershell
python -m app.twitch
```

**Important:** The module command is `python -m app.twitch`, not `python -m app.twitch.py`.

### Step 3: Authorize in Your Browser

The script starts a local server and opens the Twitch authorization page.

The current implementation requests these scopes:

* `user:read:chat`
* `chat:read`

Review the permissions and authorize the application with the Twitch account that should be used for chat access.

If the browser does not open automatically, copy the authorization URL printed or generated by the application if available. The current script calls `webbrowser.open()` to launch the authorization page.

### Step 4: Wait for Authentication to Finish

After you approve the request, Twitch redirects the browser to the local callback server.

The script then:

1. Receives the authorization code.
2. Checks the OAuth state.
3. Exchanges the code for tokens.
4. Saves the tokens.
5. Validates the access token.
6. Saves the authenticated account's user ID, login, and granted scopes.

A successful run should display:

```text
TWITCH AUTHENTICATION COMPLETE
```

It should also display the authenticated Twitch username, user ID, granted scopes, and token expiration information.

### Step 5: Protect Your Token File

The script saves the token data to:

```text
twitch_tokens.json
```

This file is generated locally and is excluded by `.gitignore`.

It contains sensitive authentication information, including access and refresh tokens.

Never:

* Commit it to GitHub.
* Send it to another user.
* Upload it to a public file-sharing service.
* Paste its contents into a public issue or chat.

If a token is exposed, revoke or replace the affected authorization as appropriate.

### Reauthentication

If the token file is missing, invalid, or unusable, follow the project's authentication process again.

The exact recovery behavior depends on the token-handling implementation.

If authentication fails, verify your Client ID, Client Secret, redirect URL, internet connection, and whether port `3000` is available.

---

## Running the Bot

Once dependencies, configuration, and authentication are complete, run the IRC entry point from the project root.

```powershell
python -m app.irc_runner
```

The bot should start its IRC connection and monitor the channels configured in `TWITCH_CHANNELS`.

Check the console output for connection messages, detected codes, authorization decisions, queue processing, and errors.

### Important: Use One Chat Receiver

The project has an IRC receiver and an EventSub implementation.

Do not run both receivers against the same channels simultaneously unless you have deliberately implemented coordination and duplicate handling for that setup.

Running multiple receivers can cause the same chat message to be processed more than once.

The normal startup command documented here is:

```powershell
python -m app.irc_runner
```

Stop the bot using `Ctrl+C` in the terminal running it.

---

## Supported Platforms and Code Detection

The code detector requires an explicit platform label before extracting a candidate code.

Examples:

```text
Steam: EXAMPLE-STEAM-CODE
Battle.net: EXAMPLE-BNET-CODE
BNet: EXAMPLE-BNET-CODE
BN: EXAMPLE-BNET-CODE
```

These are examples only.

### Case-Insensitive Detection

The platform labels are recognized without requiring a specific capitalization.

For example, the detector can recognize variations such as:

```text
STEAM: EXAMPLE-CODE
Steam: EXAMPLE-CODE
steam: EXAMPLE-CODE
```

### Multiple Platform/Code Pairs

A single message can contain more than one recognized platform/code pair.

The detector can identify separate candidates, allowing the handler to create separate jobs.

### Candidate Extraction Is Not Code Validation

The detector extracts candidate strings. It does not establish that a candidate:

* Is a valid redemption code.
* Has not expired.
* Is available to your account.
* Is valid in your region.
* Has not already been redeemed.
* Belongs to the stated platform.

The platform adapter or redemption service determines the outcome when a redemption attempt is made.

Never assume that detecting a candidate means redemption will succeed.

---

## Message Filtering and Duplicate Prevention

### Sender Authorization

The message handler checks the sender's relationship to the channel.

It accepts messages from:

* The broadcaster.
* A moderator.

Ordinary viewer messages are rejected.

This is a deliberate filtering rule, not a guarantee that every authorized message is genuine or that every candidate code is valid.

### Deduplication

The deduplicator blocks recently processed codes.

The current behavior uses the code string as the cache key and keeps entries for approximately five minutes, with a maximum cache size of 1,000 entries.

Consequently, a code seen recently may be blocked from being queued again.

The cache is in memory. Restarting the process clears the in-memory cache unless persistence is added in a future implementation.

---

## Dry-Run and Real Redemption

**Keep dry-run enabled while testing.**

The project has a dry-run setting used by the redemption workflow and platform adapters.

With dry-run enabled, the intended behavior is to simulate redemption processing rather than submit the candidate to the real redemption service.

### Dry-Run Mode

Use dry-run mode to test:

* Twitch chat message handling.
* Sender authorization.
* Platform detection.
* Candidate extraction.
* Deduplication.
* Queue creation.
* Worker processing.
* Adapter routing.
* Error handling.

Use fake adapters for tests that do not require browser automation.

When testing real adapter integration, keep dry-run enabled and verify the adapter's behavior carefully.

### Real Redemption Mode

Real redemption can have consequences, including consuming a one-time code or applying a product to an account.

Before considering real redemption:

1. Confirm the platform adapter is correct.
2. Review its behavior and failure handling.
3. Verify that the intended account is logged in.
4. Confirm how the platform indicates success or failure.
5. Test with dry-run enabled.
6. Ensure the bot cannot unintentionally submit test or placeholder values.
7. Enable real redemption only when you deliberately intend to use it.

**Never use real giveaway codes as test fixtures. Never assume a redemption failed simply because the browser or network timed out.** Confirm the actual outcome before retrying a potentially one-time code.

The precise location and behavior of the dry-run setting depend on the current configuration and adapter implementation. Check those files before changing it.

---

## Testing

The project includes tests for the detector, message pipeline, sender filtering, deduplication, queue, worker, IRC behavior, and platform-specific behavior.

Run tests from the project root with the virtual environment activated.

If `pytest` is installed in your environment, you can run:

```powershell
python -m pytest
```

This command runs tests that pytest discovers. It does not guarantee that every standalone test script will be executed.

Some project tests are standalone Python scripts and can be run individually. For example:

```powershell
python test_code_detector.py
```

```powershell
python test_message_pipeline.py
```

```powershell
python test_multiple_code_pipeline.py
```

```powershell
python test_handler_worker_integration.py
```

Run a test only if it exists in your downloaded copy of the repository.

### Important Testing Notes

* Keep the live bot stopped while running tests that use global application queues or deduplication state.
* Fake adapters are appropriate for testing job routing without real redemption.
* Browser integration tests may open a browser or use local browser state.
* Do not publish real access tokens, refresh tokens, cookies, browser profiles, or account credentials in test output.
* Use placeholder codes in tests, not real giveaway codes.
* Keep dry-run enabled when testing the real adapters.

A passing test indicates that the tested behavior worked under that test's conditions. It does not prove that every live Twitch or redemption-platform scenario will work.

---

## Project Structure

The main project files are organized approximately as follows:

```text
COD-code-bot/
│
├── app/
│   ├── config.py
│   ├── twitch.py
│   ├── auth.py
│   ├── twitch_api.py
│   ├── eventsub.py
│   ├── chat.py
│   ├── irc_chat.py
│   ├── irc_runner.py
│   ├── code_detector.py
│   ├── deduplicator.py
│   ├── message_handler.py
│   │
│   ├── redemption/
│   │   ├── base.py
│   │   ├── queue.py
│   │   ├── worker.py
│   │   ├── fake_adapters.py
│   │   ├── steam.py
│   │   └── battlenet.py
│   │
│   └── browser/
│       └── manager.py
│
├── requirements.txt
├── .env                    # Local configuration; do not commit
├── .gitignore
├── twitch_tokens.json      # Generated locally; do not commit
├── browser_profile/        # Local browser data; do not commit
└── test_*.py               # Tests, if included in the distribution
```

This is an overview of the main components. The exact list of files may change as the project evolves.

### Key Files

| File                              | Responsibility                                                    |
| --------------------------------- | ----------------------------------------------------------------- |
| `app/config.py`                   | Loads and validates environment configuration                     |
| `app/twitch.py`                   | Runs the Twitch OAuth authorization flow                          |
| `app/auth.py`                     | Exchanges, validates, saves, and loads Twitch tokens              |
| `app/irc_runner.py`               | Main IRC-based bot entry point                                    |
| `app/irc_chat.py`                 | IRC chat connection behavior                                      |
| `app/eventsub.py`                 | Alternative Twitch EventSub implementation                        |
| `app/code_detector.py`            | Detects platform labels and candidate codes                       |
| `app/deduplicator.py`             | Prevents repeated processing of recently seen codes               |
| `app/message_handler.py`          | Filters messages and creates redemption jobs                      |
| `app/redemption/queue.py`         | Manages pending redemption jobs                                   |
| `app/redemption/worker.py`        | Processes queued jobs                                             |
| `app/redemption/steam.py`         | Steam-specific redemption adapter                                 |
| `app/redemption/battlenet.py`     | Battle.net-specific redemption adapter                            |
| `app/redemption/fake_adapters.py` | Fake adapters for safe workflow testing                           |
| `app/browser/manager.py`          | Manages browser automation resources                              |
| `requirements.txt`                | Python dependencies                                               |
| `.gitignore`                      | Excludes local credentials, environments, and other ignored files |

---

## Using This Project on Another Computer

Every new user should configure their own environment and credentials.

### What to Change for Your Own Setup

| Item                 | Required action                                         |
| -------------------- | ------------------------------------------------------- |
| Python environment   | Create a new virtual environment                        |
| Dependencies         | Install from `requirements.txt`                         |
| `.env`               | Create your own file                                    |
| Twitch Client ID     | Use your own Twitch application                         |
| Twitch Client Secret | Use your own secret                                     |
| OAuth redirect URL   | Match your Twitch application settings                  |
| Twitch channels      | Configure the channel logins you want to monitor        |
| `twitch_tokens.json` | Generate your own through OAuth                         |
| Browser profile      | Allow the project to create its own local browser state |
| Dry-run setting      | Keep enabled during testing                             |
| Repository URL       | Use the actual GitHub repository URL                    |

### Recommended First-Run Sequence

1. Download or clone the repository.
2. Open the project directory in PyCharm or another editor.
3. Create and activate a virtual environment.
4. Install `requirements.txt`.
5. Install the required Playwright browser binaries.
6. Create `.env` with your own Twitch credentials.
7. Create a Twitch Developer Application.
8. Run `python -m app.twitch`.
9. Confirm that authentication completes successfully.
10. Set the channels in `TWITCH_CHANNELS`.
11. Keep dry-run enabled.
12. Run `python -m app.irc_runner`.
13. Check the console output and run the tests.

Users should not copy your `.env`, `twitch_tokens.json`, or `browser_profile` into their own installation.

---

## Troubleshooting

### `TWITCH_CLIENT_ID is missing from .env`

Ensure that `.env` exists in the project root and contains:

```dotenv
TWITCH_CLIENT_ID=YOUR_TWITCH_CLIENT_ID
```

Replace the placeholder with your actual Client ID.

### `TWITCH_CLIENT_SECRET is missing from .env`

Add the Client Secret for your own Twitch application:

```dotenv
TWITCH_CLIENT_SECRET=YOUR_TWITCH_CLIENT_SECRET
```

Never commit the real secret.

### Twitch Redirect URL Error

Confirm that the redirect URL in the Twitch Developer Console exactly matches:

```dotenv
TWITCH_REDIRECT_URI=http://localhost:3000
```

Check for differences in protocol, port, path, or trailing slash.

### Port 3000 Is Already in Use

The authentication script starts an HTTP server on `localhost:3000`.

If another application occupies that port, stop the conflicting application or deliberately update the project's callback port and matching Twitch redirect configuration. The callback server and redirect URI must remain consistent.

### Twitch Authentication Does Not Complete

Check:

* Client ID and Client Secret.
* Redirect URL.
* Internet connection.
* Whether the browser authorization was approved.
* Whether port `3000` is available.
* Whether the script received a valid authorization response.

The script only prints `TWITCH AUTHENTICATION COMPLETE` after successful token validation and final token metadata saving.

### Token File Not Found

Run the authentication command from the project root:

```powershell
python -m app.twitch
```

Confirm that authentication completes successfully and that `twitch_tokens.json` is created.

### Playwright Browser Errors

Install the browser binaries required by the installed Playwright version:

```powershell
python -m playwright install
```

If the issue persists, inspect the browser manager and adapter output to determine whether the problem is related to browser installation, login state, selectors, network access, or a changed platform page.

### No Codes Are Detected

Check whether:

* The bot is connected to the intended Twitch channel.
* The sender is the broadcaster or a moderator.
* The message includes an explicit supported platform label.
* The message format matches the detector's expectations.
* The candidate has not already been processed.

### Duplicate Code Is Ignored

The deduplicator intentionally blocks recently seen codes.

The current cache uses the code itself as its key and retains entries for approximately five minutes.

### Real Redemption Fails

Keep dry-run enabled while investigating.

Check the adapter's logs and response classification. Confirm the target account and the platform's current redemption behavior.

Do not repeatedly submit a one-time code after an ambiguous timeout. Verify whether the platform accepted it before retrying.

---

## Security Recommendations

Follow these recommendations before using or publishing the project.

### Protect Credentials

Never commit:

* `.env`
* `twitch_tokens.json`
* Twitch Client Secrets
* Access tokens or refresh tokens
* Browser cookies or browser profiles
* Other account credentials

### Keep Local Files Out of GitHub

The repository's `.gitignore` excludes several local files and directories, including:

```gitignore
.env
.venv/
__pycache__/
*.pyc
twitch_tokens.json
browser_profile/
```

These are examples of important ignore entries; preserve the complete project-specific `.gitignore`.

**Important:** `.gitignore` prevents untracked files from normally being added to Git, but it does not remove files that were already committed. Check the repository before publishing it.

### Test Safely

* Keep dry-run enabled while developing.
* Use fake adapters where possible.
* Never put real redemption codes in test fixtures.
* Avoid sharing logs that expose sensitive information.
* Stop the bot before running tests that modify shared in-memory application state.
* Never assume an uncertain redemption outcome means that the code is unused.

### Respect Platform Rules

Use Twitch and game-platform integrations in accordance with their current terms and policies. Do not attempt to bypass access controls or platform security mechanisms.

---

[//]: # ()
[//]: # (## Current Limitations)

[//]: # ()
[//]: # (The current implementation has several limitations to keep in mind:)

[//]: # ()
[//]: # (* The detector extracts candidate strings but does not independently verify code validity.)

[//]: # (* Only configured platform labels are recognized.)

[//]: # (* Sender authorization is limited to the broadcaster and moderators under the current handler logic.)

[//]: # (* Deduplication is based on code text rather than a platform-plus-code combination.)

[//]: # (* Deduplication state is in memory and does not survive a process restart.)

[//]: # (* Browser automation can break when a platform changes its login, redemption page, selectors, or response behavior.)

[//]: # (* Twitch connection and redemption success depend on network availability and platform behavior.)

[//]: # (* IRC and EventSub are separate receiving implementations and should not be run together against the same channels without deliberate coordination.)

[//]: # (* Real redemption can consume a one-time code, so ambiguous failures require careful verification.)

[//]: # ()
[//]: # (---)

[//]: # ()
[//]: # (## Future Improvements)

[//]: # ()
[//]: # (Potential improvements include:)

[//]: # ()
[//]: # (* Persistent deduplication.)

[//]: # (* More detailed logging and structured error reporting.)

[//]: # (* Additional platform adapters.)

[//]: # (* Better handling of rate limits and reconnects.)

[//]: # (* Improved configuration validation.)

[//]: # (* A more complete automated test suite.)

[//]: # (* More robust platform response classification.)

[//]: # (* Monitoring and reporting of queue status.)

[//]: # (* Optional configuration through a dedicated settings file or interface.)

[//]: # ()
[//]: # (These are potential future enhancements, not necessarily features already implemented.)

---

## License

**COD Live Code Monitor** is distributed under a custom noncommercial software license.

Copyright © 2026 Roshaan Ali Khan. All rights reserved, subject to the permissions granted by the license.

### What You Are Allowed to Do

* Use the software for personal, educational, research, and other noncommercial purposes.
* Study and modify the source code.
* Share the original software or modified versions for noncommercial purposes, provided you comply with the license's attribution and redistribution requirements.

### Attribution Requirements

If you redistribute the software or a modified version, you must:

* Credit **Roshaan Ali Khan** as the original author.
* Retain the original copyright notice and license.
* Link to the original GitHub repository when reasonably possible.
* Clearly identify any significant modifications you have made.
* Not misrepresent your modifications as the original author's work.

### Commercial Use

Commercial use is **not permitted without prior written permission** from the copyright holder.

This restriction includes selling the software or modified versions, licensing them for a fee, offering paid hosted services based on the software, or incorporating it into commercial products or services, to the extent covered by the license and applicable law.

For permission to use the software commercially, contact the copyright holder using the contact information provided in the original GitHub repository.

### Third-Party Components

Third-party libraries, dependencies, and other incorporated materials remain subject to their respective licenses and terms.

### Disclaimer

The software is provided "AS IS", without warranties of any kind, to the extent permitted by applicable law.

See the [`LICENSE`](LICENSE) file for the complete terms and conditions.
