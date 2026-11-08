#  Telegram Train Monitor Bot

A Python-based Telegram bot designed for commuters. It automates the tracking of trains (Trenitalia / Trenord) and sends customized notifications based on your travel schedule.

This bot is designed to run 24/7 on free cloud services like Render.com, bypassing anti-bot blocks via a Proxy API and keeping the infrastructure awake automatically.

##  Key Features

- **On-Demand Monitoring:** Send the bot your train time and instantly receive the status and current delay.
- **Morning Automation:** At the scheduled time, the bot wakes up and starts monitoring the train in the background for you.
- **Smart Alerts:**
  - Notification when the train physically departs from the origin station.
  - Notification when passing a chosen intermediate station (your cue to leave the house).
  - Immediate alerts in case of a canceled or limited train.
- **Anti-Bot Bypass:** Integrated with ScraperAPI to avoid institutional IP blocks typical of cloud servers.

##  Prerequisites

To run this bot, you will need:
1. A **Telegram Bot Token** (obtainable via [@BotFather](https://t.me/botfather)).
2. Your **Telegram ID** to restrict the bot's usage to yourself (e.g., via [@userinfobot](https://t.me/userinfobot)).
3. A free account on **Render.com** (to host the code).
4. A free account on **ScraperAPI** (to get the Proxy Key).
5. A free account on **cron-job.org** (to keep the server always awake).

## ⚙️ Environment Variables

Configure the following variables on your server (e.g., Render.com -> Environment) to make the bot work:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `BOT_TOKEN` | ` ` | The token provided by BotFather. |
| `MIO_ID` | ` ` | Your numeric Telegram ID. |
| `SCRAPER_API_KEY` | ` ` | API Key obtained from ScraperAPI. |
| `TZ` | ` ` | Server timezone (crucial for alarms). |
| `TRENO_1` | ` ` | Number of the first train to monitor. |
| `STAZIONE_1` | ` ` | Reference station for the arrival alert. |
| `SVEGLIA_ORA_1` | ` ` | Hour to start the automatic monitoring. |
| `SVEGLIA_MIN_1` | ` ` | Minute to start the automatic monitoring. |
| `GIORNI_1` | ` ` | Days of the week for activation. |
| `ORARIO_DB_1` | ` ` | Time to type in chat for manual checks. |

*(Note: Repeat the variables `TRENO_2`, `STAZIONE_2`, etc. for your return trip).*

##  Installation and Deployment

1. **Fork** or clone this repository.
2. Create a new **Web Service** on Render.com and link it to your GitHub repository.
3. Insert all the environment variables listed above.
4. Complete the deployment. Render will automatically install the requirements (make sure you have a `requirements.txt` file).
5. Copy the URL Render provides at the end of the deployment (e.g., `https://your-bot.onrender.com`).
6. Go to **cron-job.org**, create a new Cronjob, paste the URL, and set it to make a `GET` request every 14 minutes. This prevents Render from putting the bot to sleep due to inactivity.

## 🛠 Built With

* [Python](https://www.python.org/) - Base language.
* [Aiogram](https://docs.aiogram.dev/) - Telegram bot framework.
* [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling.
* [Aiohttp](https://docs.aiohttp.org/) - Asynchronous HTTP client.
