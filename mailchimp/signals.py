from django.dispatch import Signal

args = ["list", "fired_at", "email", "interests", "fname", "lname", "merges"]

mc_subscribe = Signal(providing_args=args)
mc_unsubscribe = Signal(providing_args=args)
mc_profile = Signal(providing_args=args)
mc_upemail = Signal(providing_args=["list", "old_email", "new_email", "fired_at"])
mc_cleaned = Signal(providing_args=["fired_at", "list", "reason", "email"])
mc_campaign = Signal(providing_args=["fired_at", "list", "campaign_id", "reason", "status", "subject"])


def get_signal(name):
    return globals()['mc_%s' % name]
