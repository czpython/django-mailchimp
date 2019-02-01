import math

from datetime import timedelta



def transform_datetime(dt):
    """ converts datetime parameter"""

    if dt is None:
        dt = ''
    else:
        dt = dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt


def ceil_dt(dt):
    # Taken from http://stackoverflow.com/a/13071613/389453
    # how many secs have passed this hour
    nsecs = dt.minute * 60 + dt.second + dt.microsecond*1e-6
    # number of seconds to next quarter hour mark
    # Non-analytic (brute force is fun) way:
    delta = next(x for x in xrange(0,3601,900) if x>=nsecs) - nsecs
    # time + number of seconds to quarter hour mark.
    return dt + timedelta(seconds=delta)


def flatten(params, key=None):
    """ flatten nested dictionaries and lists """
    flat = {}
    for name, val in params.items():
        if key is not None and not isinstance(key, int):
            name = "{}[{}]".format(key, name)
        if isinstance(val, dict):
            flat.update(flatten(val, name))
        elif isinstance(val, list):
            flat.update(flatten(dict(enumerate(val)), name))
        elif val is not None:
            flat[name] = val
    return flat
