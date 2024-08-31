from __future__ import annotations

import os
import logging
from typing import TYPE_CHECKING, Any, Callable

from pytz import timezone
from dotenv import load_dotenv
from slack_bolt import App
from apscheduler.triggers.cron import CronTrigger
from slack_bolt.adapter.socket_mode import SocketModeHandler
from apscheduler.schedulers.background import BackgroundScheduler

if TYPE_CHECKING:
  from logging import Logger

  from slack_sdk.web import SlackResponse

load_dotenv()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = App(token=os.environ.get("SLACK_BOT_TOKEN"), signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))
PYSILO_CHANNEL_ID = "C07K19HE4P6"


@app.middleware
def log_request(logger: Logger, body: dict, next: Callable) -> None:
  logger.debug(f"Received request: {body}")
  next()


@app.error
def custom_error_handler(error: Exception, body: dict[str, Any], logger: Logger) -> None:
  logger.exception(f"Error: {error}")
  logger.info(f"Request body: {body}")


@app.event("message")
def handle_message_events(body: dict[str, Any], logger: Logger) -> None:
  event: dict[str, Any] = body["event"]
  if event.get("channel_type") == "im":
    user: str = event["user"]
    logger.info(f"Received DM from user {user}")
    channel: str = event["channel"]
    try:
      response: SlackResponse = app.client.chat_postMessage(
        channel=channel,
        text=f"Hi <@{user}>! Just a friendly reminder that it's often beneficial to post questions or discussions in public channels. This allows others to learn from the conversation and contribute their insights. Of course, for sensitive or personal matters, direct messages are still appropriate.",
      )
      assert response["ok"], "Message sending failed"
    except Exception as e:
      logger.error(f"Error posting message: {e}")


def post_regular_updates() -> None:
  try:
    response: SlackResponse = app.client.chat_postMessage(channel=PYSILO_CHANNEL_ID, text="Reminder: Please post your updates!")
    assert response["ok"], "Message sending failed"
    logger.info(f"Posted a regular update to the channel with ID {PYSILO_CHANNEL_ID}")
  except Exception as e:
    logger.error(f"Error posting regular update: {e}")


def start_scheduler() -> None:
  scheduler = BackgroundScheduler()
  scheduler.add_job(post_regular_updates, CronTrigger(day_of_week="mon,wed,fri", hour=12, minute=0, timezone=timezone("America/New_York")))
  scheduler.start()


@app.event("app_mention")
def handle_app_mentions(body: dict[str, Any], say: Callable[[str], None]) -> None:
  event: dict[str, Any] = body["event"]
  user: str = event["user"]
  say(f"Hi there, <@{user}>! I'm here to help. How can I assist you today?")


def main() -> None:
  start_scheduler()
  handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
  handler.start()


if __name__ == "__main__":
  main()
