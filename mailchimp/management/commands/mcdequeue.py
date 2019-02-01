from django.core.management import BaseCommand
from mailchimp.utils import dequeue
from optparse import make_option


class Command(BaseCommand):

    def handle(self, *args, **options):
        if len(args) and args[0].isdigit():
            limit = int(args[0])
        else:
            limit = None
        print('Dequeueing Campaigns')
        done = False
        for camp in dequeue(limit):
            done = True
            if camp:
                print('- Dequeued campaign {} ({})'.format(camp.name, camp.campaign_id))
            else:
                print('ERROR')
        if not done:
            print('Nothing to dequeue')
        print('Done')