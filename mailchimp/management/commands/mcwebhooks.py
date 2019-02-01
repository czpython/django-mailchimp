from django.core.management import BaseCommand
from mailchimp.utils import get_connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Installing webhooks for all lists')
        c = get_connection()
        for list in c.lists.values():
            print('Checking list {}'.format(list.name))
            # def add_webhook_if_not_exists(self, url, actions, sources):
            if list.install_webhook():
                print('  ok')
            else:
                print('  ERROR!')
        print('Done')