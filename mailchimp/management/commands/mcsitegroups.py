from django.core.management import BaseCommand
from django.contrib.sites.models import Site
from mailchimp.utils import get_connection


class Command(BaseCommand):
    def handle(self, *args, **options):
        print('Installing site segment groups for all lists and all sites')
        c = get_connection()
        interests = []
        for site in Site.objects.all():
            interests.append(site.domain)
        for list in c.lists.values():
            print('Checking list {}'.format(list.name))
            list.add_interests_if_not_exist(*interests)
            print('  ok')
        print('Done')