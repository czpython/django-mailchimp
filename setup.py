from setuptools import setup, find_packages

setup(
    name = 'django-mailchimp-v1.3',
    version = 1.3, # Otherwise buildout fails
    description = 'Mailchimp wrapper for Django, using Mailchimp API 1.3',
    author = 'Jonas Obrist et al.',
    url = 'http://github.com/piquadrat/django-mailchimp',
    packages = find_packages(),
    zip_safe=False,
    package_data={
        'mailchimp': [
            'templates/mailchimp/*.html',
            'locale/*/LC_MESSAGES/*',
        ],
    },
)
