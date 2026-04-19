from django.core.management.base import BaseCommand
from telegram_bot.bot_logic import run_bot


class Command(BaseCommand):
    help = 'Run the full-featured FarmBuddy Telegram Bot (bot_logic.py)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting FarmBuddy bot (bot_logic)...'))
        run_bot()
