# Uni SMS Bot

A Telegram bot for buying and renting virtual phone numbers using the onlinesim.io API.

## Features

- **Buy Numbers:** Purchase temporary numbers for various services with a user-friendly, paginated interface.
- **Rent Numbers:** Rent numbers for longer periods, with options to view SMS history, extend, and close the rental.
- **Free Numbers:** Browse a list of public, free-to-use numbers and read their incoming SMS.
- **Account Balance:** Check your onlinesim.io account balance at any time.
- **User History:** View your personal history of purchased and rented numbers.
- **Live Support:** A direct chat feature to connect with a bot admin for support.
- **Referral System:** Users can be referred by others (tracked by user ID).

## Setup and Installation

1.  **Get the code:**
    Clone this repository or download the source files.
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a Virtual Environment:**
    It is highly recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    Install all the required Python packages from the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The bot is configured using environment variables for security. The application will read these variables on startup.

You need to set the following environment variables:

- `API_ID`: Your Telegram API ID.
- `API_HASH`: Your Telegram API Hash.
- `BOT_TOKEN`: The token for your Telegram bot from BotFather.
- `ONLINE_SIM_API_KEY`: Your API key from onlinesim.io.
- `ADMIN_ID`: The Telegram User ID of the person who will act as the support agent.

**How to set environment variables:**

- **Linux/macOS:**
  ```bash
  export BOT_TOKEN="your_token_here"
  ```
- **Windows:**
  ```bash
  set BOT_TOKEN="your_token_here"
  ```

Alternatively, you can create a `.env` file in the project root and use a library like `python-dotenv` to load them (though this is not included by default).

## Running the Bot

Once you have installed the dependencies and configured the environment variables, you can run the bot with the following command:

```bash
python main.py
```

The bot will start, register all its handlers, and begin listening for messages.

## Project Structure

The project is organized into several directories to keep the code clean and maintainable:

- `main.py`: The main entry point of the application.
- `config.py`: Reads and provides configuration from environment variables.
- `requirements.txt`: Lists all Python dependencies.
- `bot/`: The main package for the bot's logic.
  - `api.py`: An asynchronous wrapper for the onlinesim.io API.
  - `db.py`: Manages the SQLite database for user data and history.
  - `utils.py`: Contains helper functions, like the keyboard paginator.
  - `handlers/`: Contains all the message and callback handlers, separated by feature.
  - `keyboards/`: Contains functions for generating reusable inline keyboards.
- `uni_sms.db`: The SQLite database file (will be created on the first run).
