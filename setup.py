from setuptools import setup, find_packages

version = __import__('mailchimp').__version__

setup(
    name = 'django-mailchimp-v1.3',
    version = version,
    description = 'Mailchimp wrapper for Django, using Mailchimp API 1.3',
    author = 'Jonas Obrist et al.',
    url = 'http://github.com/divio/django-mailchimp',
    packages = find_packages(),
    zip_safe=False,
    package_data={
        'mailchimp': [
            'templates/mailchimp/*.html',
            'locale/*/LC_MESSAGES/*',
        ],
    },
)
