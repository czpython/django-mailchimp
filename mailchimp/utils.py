import json
import re
import warnings

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import logout
from django.contrib.messages import debug, info, success, warning, error, add_message
from django.http import (
    HttpResponse, HttpResponseForbidden, Http404, HttpResponseNotAllowed,
    HttpResponseRedirect, HttpResponsePermanentRedirect, HttpResponseNotModified,
    HttpResponseBadRequest, HttpResponseNotFound, HttpResponseGone,
    HttpResponseServerError
)
from mailchimp.settings import API_KEY, SECURE, REAL_CACHE, CACHE_TIMEOUT

class KeywordArguments(dict):
    def __getattr__(self, attr):
        return self[attr]


class Cache(object):
    def __init__(self, prefix=''):
        self._data = {}
        self._clear_lock = False
        self._prefix = prefix
        if REAL_CACHE:
            self._set = getattr(self, '_real_set')
            self._get = getattr(self, '_real_get')
            self._del = getattr(self, '_real_del')
        else:
            self._set = getattr(self, '_fake_set')
            self._get = getattr(self, '_fake_get')
            self._del = getattr(self, '_fake_del')


    def get(self, key, obj, *args, **kwargs):
        if self._clear_lock:
            self.flush(key)
            self._clear_lock = False
        value = self._get(key)
        if value is None:
            value = obj(*args, **kwargs) if callable(obj) else obj
            self._set(key, value)
        return value

    def _real_set(self, key, value):
        cache.set(key, value, CACHE_TIMEOUT)

    def _real_get(self, key):
        return cache.get(key, None)

    def _real_del(self, key):
        cache.delete(key)

    def _fake_set(self, key, value):
        self._data[key] = value

    def _fake_get(self, key):
        return self._data.get(key, None)

    def _fake_del(self, key):
        if key in self._data:
            del self._data[key]

    def get_child_cache(self, key):
        return Cache('%s_%s_' % (self._prefix, key))

    def flush(self, *keys):
        for key in keys:
            if key in self._data:
                self._del(key)

    def lock(self):
        self._clear_lock = True

    def clear(self, call):
        self.lock()
        return call()


def wrap(base, parent, name, *baseargs, **basekwargs):
    def _wrapped(*args, **kwargs):
        fullargs = baseargs + args
        kwargs.update(basekwargs)
        return getattr(parent, '%s_%s' % (base, name))(*fullargs, **kwargs)
    return _wrapped


def build_dict(master, klass, data, key='id'):
    return  dict([(info[key], klass(master, info)) for info in data])

def _convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class Bullet(object):
    def __init__(self, number, link, active):
        self.number = number
        self.link = link
        self.active = active


class Paginator(object):
    def __init__(self, objects, page, get_link, per_page=20, bullets=5):
        page = int(page)
        self.page = page
        self.get_link = get_link
        self.all_objects = objects
        self.objects_count = objects.count()
        per_page = per_page() if callable(per_page) else per_page
        self.pages_count = int(float(self.objects_count) / float(per_page)) + 1
        self.bullets_count = 5
        self.per_page = per_page
        self.start = (page - 1) * per_page
        self.end = page * per_page
        self.is_first = page == 1
        self.first_bullet = Bullet(1, self.get_link(1), False)
        self.is_last = page == self.pages_count
        self.last_bullet = Bullet(self.pages_count, self.get_link(self.pages_count), False)
        self.has_pages = self.pages_count != 1
        self._objects = None
        self._bullets = None

    @property
    def bullets(self):
        if self._bullets is None:
            pre = int(float(self.bullets_count) / 2)
            bullets = [Bullet(self.page, self.get_link(self.page), True)]
            diff = 0
            for i in range(1, pre + 1):
                this = self.page - i
                if this:
                    bullets.insert(0, Bullet(this, self.get_link(this), False))
                else:
                    diff = pre - this
                    break
            for i in range(1, pre + 1 + diff):
                this = self.page +  i
                if this <= self.pages_count:
                    bullets.append(Bullet(this, self.get_link(this), False))
                else:
                    break
            self._bullets = bullets
        return self._bullets

    @property
    def objects(self):
        if self._objects is None:
            self._objects = self.all_objects[self.start:self.end]
        return self._objects


class InternalRequest(object):
    def __init__(self, request, args, kwargs):
        self.request = request
        self.args = args
        self.kwargs = kwargs

    def contribute_to_class(self, cls):
        cls.request = self.request
        cls.args = self.args
        cls.kwargs = self.kwargs


class BaseView(object):
    """
    A base class to create class based views.

    It will automatically check allowed methods if a list of allowed methods are
    given. It also automatically tries to route to 'handle_`method`' methods if
    they're available. So if for example you define a 'handle_post' method and
    the request method is 'POST', this one will be called instead of 'handle'.

    For each request a new instance of this class will be created and it will get
    three attributes set: request, args and kwargs.
    """
    # A list of allowed methods (if empty any method will be allowed)
    allowed_methods = []
    # The template to use in the render_to_response helper
    template = 'base.html'
    # Only allow access to logged in users
    login_required = False
    # Only allow access to users with certain permissions
    required_permissions = []
    # Only allow access to superusers
    superuser_required = False
    # Response to send when request is automatically declined
    auto_decline_response = 'not_found'

    #===========================================================================
    # Dummy Attributes (DO NOT OVERWRITE)
    #===========================================================================
    request = None
    args = tuple()
    kwargs = {}

    #===========================================================================
    # Internal Methods
    #===========================================================================

    def __init__(self, *args, **kwargs):
        # Preserve args and kwargs
        self._initial_args = args
        self._initial_kwargs = kwargs

    @property
    def __name__(self):
        """
        INTERNAL: required by django
        """
        return self.get_view_name()

    def __call__(self, request, *args, **kwargs):
        """
        INTERNAL: Called by django when a request should be handled by this view.
        Creates a new instance of this class to sandbox
        """
        if self.allowed_methods and request.method not in self.allowed_methods:
            return getattr(self, self.auto_decline_response)()
        if self.login_required and not request.user.is_authenticated():
            return getattr(self, self.auto_decline_response)()
        if self.superuser_required and not request.user.is_superuser:
            return getattr(self, self.auto_decline_response)()
        if self.required_permissions and not request.user.has_perms(self.required_permissions):
            return getattr(self, self.auto_decline_response)()
        handle_func_name = 'handle_%s' % request.method.lower()
        if not hasattr(self, handle_func_name):
            handle_func_name = 'handle'
        # Create a sandbox instance of this class to safely set the request, args and kwargs attributes
        sandbox = self.__class__(*self._initial_args, **self._initial_kwargs)
        sandbox.args = args
        sandbox.kwargs = kwargs
        sandbox.request = request
        return getattr(sandbox, handle_func_name)()

    #===========================================================================
    # Misc Helpers
    #===========================================================================

    def get_view_name(self):
        """
        Returns the name of this view
        """
        return self.__class__.__name__

    def get_template(self):
        return self.template

    def logout(self):
        logout(self.request)


    def get_page_link(self, page):
        return '%s?page=%s' % (self.request.path, page)

    def paginate(self, objects, page):
        return Paginator(objects, page, self.get_page_link, 20, 5)

    def reverse(self, view_name, *args, **kwargs):
        return reverse(view_name, args=args or (), kwargs=kwargs or {})

    #===========================================================================
    # Handlers
    #===========================================================================

    def handle(self):
        """
        Write your view logic here
        """
        pass

    #===========================================================================
    # Response Helpers
    #===========================================================================

    def not_allowed(self, data=''):
        return HttpResponseNotAllowed(data)

    def forbidden(self, data=''):
        return HttpResponseForbidden(data)

    def redirect(self, url):
        return HttpResponseRedirect(url)

    def named_redirect(self, viewname, urlconf=None, args=None, kwargs=None,
            prefix=None, current_app=None):
        return self.redirect(reverse(view, urlconf, args, kwargs, prefix, current_app))

    def permanent_redirect(self, url):
        return HttpResponsePermanentRedirect(url)

    def named_permanent_redirect(self, viewname, urlconf=None, args=None,
            kwargs=None, prefix=None, current_app=None):
        return self.permanent_redirect(reverse(view, urlconf, args, kwargs, prefix, current_app))

    def not_modified(self, data=''):
        return HttpResponseNotModified(data)

    def bad_request(self, data=''):
        return HttpResponseBadRequest(data)

    def not_found(self, data=''):
        return HttpResponseNotFound(data)

    def gone(self, data=''):
        return HttpResponseGone(data)

    def server_error(self, data=''):
        return HttpResponseServerError(data)

    def json(self, data):
        return HttpResponse(json.dumps(data), content_type='application/json')

    def response(self, data):
        return HttpResponse(data)

    def render_to_response(self, data, request_context=True):
        if request_context:
            return render_to_response(self.get_template(), data, RequestContext(self.request))
        return render_to_response(self.get_template(), data)

    #===========================================================================
    # Message Helpers
    #===========================================================================

    def message_debug(self, message):
        debug(self.request, message)

    def message_info(self, message):
        info(self.request, message)

    def message_success(self, message):
        success(self.request, message)

    def message_warning(self, message):
        warning(self.request, message)

    def message_error(self, message):
        error(self.request, message)

    def add_message(self, msgtype, message):
        add_message(self.request, msgtype, message)


class WarningProxy(object):
    __stuff = {}

    def __init__(self, logger, obj):
        WarningProxy.__stuff[self] = {}
        WarningProxy.__stuff[self]['logger'] = logger
        WarningProxy.__stuff[self]['obj'] = obj

    def __getattr__(self, attr):
        WarningProxy.__stuff[self]['logger'].lock()
        val = getattr(WarningProxy.__stuff[self]['obj'], attr)
        WarningProxy.__stuff[self]['logger'].release()
        return WarningProxy(WarningProxy.__stuff[self]['logger'], val)

    def __setattr__(self, attr, value):
        WarningProxy.__stuff[self]['logger'].lock()
        setattr(WarningProxy.__stuff[self]['obj'], attr)
        WarningProxy.__stuff[self]['logger'].release()

    def __call__(self, *args, **kwargs):
        WarningProxy.__stuff[self]['logger'].lock()
        val = WarningProxy.__stuff[self]['obj'](*args, **kwargs)
        WarningProxy.__stuff[self]['logger'].release()
        return val


class WarningLogger(object):
    def __init__(self):
        self.proxies = []
        self.queue = []
        self._old = warnings.showwarning

    def proxy(self, obj):
        return WarningProxy(self, obj)

    def lock(self):
        warnings.showwarning = self._showwarning

    def _showwarning(self, message, category, filename, lineno, fileobj=None):
        self.queue.append((message, category, filename, lineno))
        self._old(message, category, filename, lineno, fileobj)

    def release(self):
        warnings.showwarning = self._old

    def get(self):
        queue = list(self.queue)
        self.queue = []
        return queue

    def reset(self):
        self.queue = []


class Lazy(object):
    def __init__(self, real):
        self.__real = real
        self.__cache = {}

    def __getattr__(self, attr):
        if attr not in self.__cache:
            self.__cache[attr] = getattr(self.__real, attr)
        return self.__cache[attr]


def dequeue(limit=None):
    from mailchimp.models import Queue
    for camp in Queue.objects.dequeue(limit):
        yield camp

def is_queued_or_sent(object):
    from mailchimp.models import Queue, Campaign
    object_id = object.pk
    content_type = ContentType.objects.get_for_model(object)
    q = Queue.objects.filter(content_type=content_type, object_id=object_id)
    if q.count():
        return q[0]
    c = Campaign.objects.filter(content_type=content_type, object_id=object_id)
    if c.count():
        return c[0]
    return False

# this has to be down here to prevent circular imports
from mailchimp.chimp import Connection
# open a non-connected connection (lazily connect on first get_connection call)
CONNECTION = Connection(secure=SECURE)

def get_connection():
    if not CONNECTION.is_connected:
        CONNECTION.connect(API_KEY)
    return CONNECTION
