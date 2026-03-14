from django.core.management.base import BaseCommand
from telegram_bot.bot_logic import run_bot

class Command(BaseCommand):
    help = 'Runs the Telegram bot polling loop'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting FarmBuddy Telegram Bot...'))
        run_bot()
