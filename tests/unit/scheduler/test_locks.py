# -*- coding: ascii -*-
r"""
:Copyright:

 Copyright 2014 - 2016
 Andr\xe9 Malo or his licensors, as applicable

:License:

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

==================================
 Tests for wolfe.scheduler._locks
==================================

Tests for wolfe.scheduler._locks.
"""
if __doc__:  # pragma: no cover
    # pylint: disable = redefined-builtin
    __doc__ = __doc__.encode('ascii').decode('unicode_escape')
__author__ = r"Andr\xe9 Malo".encode('ascii').decode('unicode_escape')
__docformat__ = "restructuredtext en"

import collections as _collections

from nose.tools import assert_equals, assert_raises, assert_false, assert_true
from ... import _util as _test

from wolfe.scheduler import _locks


# pylint: disable = unused-argument
# pylint: disable = protected-access
# pylint: disable = pointless-statement
# pylint: disable = no-member


class _Scheduler(object):
    """ Sample scheduler """
    just_me = id(_locks)


def _lock(name, exclusive=True):
    """ Create lock dummy """
    return _test.Bunch(**locals())


def test_locks_init():
    """ Locks initializes properly """
    scheduler = _Scheduler()
    locks = _locks.Locks(scheduler)

    assert_equals(locks._scheduler.just_me, scheduler.just_me)
    assert_equals(type(locks._acquired), dict)
    assert_equals(type(locks._waiting), _collections.defaultdict)
    assert_equals(locks._waiting.default_factory, set)
    assert_equals(type(locks._free), _collections.defaultdict)
    assert_equals(locks._free.default_factory, set)

    # scheduler should be weakref'd. Test that by deleting our reference:
    del scheduler
    with assert_raises(ReferenceError):
        locks._scheduler.just_me


def test_locks_enter():
    """ Locks.enter enters locks properly """
    scheduler = _test.mock.MagicMock()
    job = _test.Bunch(locks=(_lock('foo'), _lock('bar')), id=42)

    locks = _locks.Locks(scheduler)
    locks._acquired['foo'] = 1

    locks.enter(job)

    assert_equals(job.locks_waiting, 1)
    assert_equals(locks._waiting, {'foo': set([42])})
    assert_equals(locks._free, {'bar': set([42])})
    assert_equals(locks._acquired, {'foo': 1})


def test_locks_acquire_false():
    """ Locks.acquire rejects waiting job """
    scheduler = _test.mock.MagicMock()
    job = _test.Bunch(locks_waiting=1)

    locks = _locks.Locks(scheduler)

    assert_false(locks.acquire(job))


def test_locks_acquire_true():
    """ Locks.acquire acquires locks properly """
    scheduler = _test.mock.MagicMock()
    job = _test.Bunch(id=24, locks=(_lock('foo'), _lock('bar')))
    job2 = _test.Bunch(id=25, locks=(_lock('foo'),))
    scheduler.jobs = {24: job, 25: job2}

    locks = _locks.Locks(scheduler)
    locks._acquired['baz'] = 2
    locks.enter(job)
    locks.enter(job2)

    assert_equals(job.locks_waiting, 0)
    assert_equals(job2.locks_waiting, 0)
    assert_equals(locks._waiting, {})
    assert_equals(locks._free, {'foo': set([24, 25]), 'bar': set([24])})
    assert_equals(locks._acquired, {'baz': 2})

    assert_true(locks.acquire(job))

    assert_equals(job.locks_waiting, 0)
    assert_equals(job2.locks_waiting, 1)
    assert_equals(locks._waiting, {'foo': set([25])})
    assert_equals(locks._free, {})
    assert_equals(locks._acquired, {'baz': 2, 'foo': 24, 'bar': 24})


def test_locks_release():
    """ Locks.release releases locks properly """
    scheduler = _test.mock.MagicMock()

    job = _test.Bunch(id=24, locks=(_lock('foo'), _lock('bar')))
    job2 = _test.Bunch(id=25, locks=(_lock('foo'),))
    job3 = _test.Bunch(id=26, locks=(_lock('bar'), _lock('zonk')))
    scheduler.jobs = {24: job, 25: job2, 26: job3}

    locks = _locks.Locks(scheduler)
    locks._acquired['baz'] = 3
    locks.enter(job)
    locks.enter(job2)
    locks.enter(job3)

    assert_equals(job.locks_waiting, 0)
    assert_equals(job2.locks_waiting, 0)
    assert_equals(job3.locks_waiting, 0)
    assert_equals(locks._waiting, {})
    assert_equals(locks._free, {
        'foo': set([24, 25]),
        'bar': set([24, 26]),
        'zonk': set([26]),
    })
    assert_equals(locks._acquired, {'baz': 3})

    assert_true(locks.acquire(job2))
    assert_true(locks.acquire(job3))

    assert_equals(job.locks_waiting, 2)
    assert_equals(job2.locks_waiting, 0)
    assert_equals(job3.locks_waiting, 0)
    assert_equals(locks._waiting, {'foo': set([24]), 'bar': set([24])})
    assert_equals(locks._free, {})
    assert_equals(locks._acquired, {
        'baz': 3,
        'foo': 25,
        'bar': 26,
        'zonk': 26,
    })

    assert_equals(locks.release(job2), [])

    assert_equals(job.locks_waiting, 1)
    assert_equals(job2.locks_waiting, 0)
    assert_equals(job3.locks_waiting, 0)
    assert_equals(locks._waiting, {'bar': set([24])})
    assert_equals(locks._free, {'foo': set([24])})
    assert_equals(locks._acquired, {'baz': 3, 'bar': 26, 'zonk': 26})

    assert_equals(locks.release(job3), [job])

    assert_equals(job.locks_waiting, 0)
    assert_equals(job2.locks_waiting, 0)
    assert_equals(job3.locks_waiting, 0)
    assert_equals(locks._waiting, {})
    assert_equals(locks._free, {'foo': set([24]), 'bar': set([24])})
    assert_equals(locks._acquired, {'baz': 3})
