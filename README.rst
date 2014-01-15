=====================
Django Mailchimp v1.3
=====================

This is an integrated app for Django dealing with the Mailchimp mailing list system.

.. warning::
    This package used to be called simply ``django-mailchimp``. But since the
    mailchimp API changed in non-backwards-compatible ways between v1.2 and v1.3,
    we renamed it to ``django-mailchimp-v1.3``.

    Stuff may break in funny ways with this release, so make sure to thoroughly
    test your code if you want to update from ``django-mailchimp``.

Quick start guide:
------------------

Installation:
*************

1. Install ``django-mailchimp-v1.3``::

    pip install django-mailchimp-v1.3

2. Add a ``MAILCHIMP_API_KEY`` to your settings.py with your mailchimp API key as the value (obviously)

3. Add ``mailchimp`` to your project's list of INSTALLED_APPS

4. To start using the API, you should start by using utils.get_connection(). This will use the API_KEY you
just defined in settings.py


Subscribing a user to a list:
*****************************

1. To get the list::

    list = mailchimp.utils.get_connection().get_list_by_id(<list key id>)

2. Now add a member to the mailing list::

    list.subscribe('example@example.com', {'EMAIL':'example@example.com'})


Those pesky merge vars:
-----------------------

General info:
*************

Mailchimp is a quite generic service. As such, it needs to store information on people who subscribe to a list,
and that information is specific to this very list!

So to help you build dynamic forms (presumabely), mailchimp added the merge_vars. They are, basically, a 
dictionnary showing infromation and meta-information defined for each piece of information.
Here's what the default set of merge vars look like (ona  brand new list with default options)::

    [
        {
        'field_type': 'email', 
        'name': 'Email Address', 
        'show': True, 
        'default': None, 
        'req': True, 
        'public': True, 
        'tag': 'EMAIL', 
        'helptext': None, 
        'order': '1', 
        'size': '25'
        },{
        'field_type': 'text', 
        'name': 'First Name', 
        'show': True, 
        'default': '', 
        'req': False, 
        'public': True, 
        'tag': 'FNAME', 
        'helptext': '', 
        'order': '2', 
        'size': '25'
        },{
        'field_type': 'text', 
        'name': 'Last Name', 
        'show': True, 
        'default': '', 
        'req': False, 
        'public': True, 
        'tag': 'LNAME', 
        'helptext': '', 
        'order': '3', 
        'size': '25'
        }
    ]

As you can see, it's a list of 3 dictionnaries, each containing several fields that you should use to build your 
user interface with (since you're using this app, that means your Django form).

Obtaining them:
***************

You can recreate this list using the following API call::

    list = mailchimp.utils.get_connection().get_list_by_id(<The list's key ID>)
    print list.merges


Using them:
***********

When you make a post to mailchimp, you need to pass merge_vars. For example, in a new list created with the default
settings on the mailchimp website, the following call adds a member to a list (with a little more info than our bare minimum example up there)::

    list = mailchimp.utils.get_connection().get_list_by_id(<The list's key ID>)
    list.subscribe('example@example.com', {'EMAIL': 'example@example.com', 'FNAME': 'Monthy', 'LNAME': 'Pythons'})

Note the use of the 'tag' field as the key for fields (why they didn't call it 'key' or 'id' is beyond comprehension).



Create a view:
--------------

We'll now try to move up the stack and create the necessary elements to make a useable mailchimp interface

Fire up your favorite editor and open your views.py. Put in the following snippet of code::

    from django.http import HttpResponseRedirect
    from mailchimp import utils

    MAILCHIMP_LIST_ID = 'spamspamspamspameggsspamspam' # DRY :)
    REDIRECT_URL_NAME = '/mailing_list_success/'
    def add_email_to_mailing_list(request):
        if request.POST['email']:
            email_address = request.POST['email']
            list = utils.get_connection().get_list_by_id(MAILCHIMP_LIST_ID)
            list.subscribe(email_address, {'EMAIL': email_address})
            return HttpResponseRedirect('/mailing_list_success/')
        else:
            return HttpResponseRedirect('/mailing_list_failure/')

Of course, if you feel redirecting the user is not the right approach (handling a form might be a good idea), feel
free to adapt this simple example to your needs :p


