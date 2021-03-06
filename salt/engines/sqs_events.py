# -*- coding: utf-8 -*-
'''
An engine that continuously reads messages from SQS and fires them as events.
'''
# Import salt libs
import salt.utils.event

# Import python libs
import logging

# Import third party libs
try:
    import boto.sqs
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

from salt.ext.six import string_types


def __virtual__():
    if not HAS_BOTO:
        return False
    else:
        return True


log = logging.getLogger(__name__)


def _get_sqs_conn(profile):
    '''
    Get a boto connection to SQS.
    '''
    if profile:
        if isinstance(profile, string_types):
            _profile = __opts__[profile]
        elif isinstance(profile, dict):
            _profile = profile
        key = _profile.get('key', None)
        keyid = _profile.get('keyid', None)
        region = _profile.get('region', None)

    if not region and __opts__.get('sqs.region'):
        region = __opts__.get('sqs.region')

    if not region:
        region = 'us-east-1'

    if not key and __opts__.get('sqs.key'):
        key = __opts__.get('sqs.key')
    if not keyid and __opts__.get('sqs.keyid'):
        keyid = __opts__.get('sqs.keyid')

    try:
        conn = boto.sqs.connect_to_region(region, aws_access_key_id=keyid,
                                          aws_secret_access_key=key)
    except boto.exception.NoAuthHandlerFound:
        log.error('No authentication credentials found when attempting to'
                  ' make sqs_event engine connection to AWS.')
        return None
    return conn


def start(queue, profile=None):
    '''
    Listen to events and write them to a log file
    '''
    if __opts__.get('__role') == 'master':
        event_bus = salt.utils.event.get_master_event(
            __opts__,
            __opts__['sock_dir'])
    else:
        event_bus = salt.utils.event.get_event(
            'minion',
            transport=__opts__['transport'],
            opts=__opts__,
            sock_dir=__opts__['sock_dir'])
    sqs = _get_sqs_conn(profile)
    q = sqs.get_queue(queue)

    while True:
        msgs = q.get_messages(wait_time_seconds=1000)
        for msg in msgs:
            event_bus.fire_event({'message': msg.get_body()},
                                 'salt/engine/sqs')
            msg.delete()
