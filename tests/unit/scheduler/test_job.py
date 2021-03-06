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

================================
 Tests for wolfe.scheduler._job
================================

Tests for wolfe.scheduler._job.
"""
if __doc__:  # pragma: no cover
    # pylint: disable = redefined-builtin
    __doc__ = __doc__.encode('ascii').decode('unicode_escape')
__author__ = r"Andr\xe9 Malo".encode('ascii').decode('unicode_escape')
__docformat__ = "restructuredtext en"

import itertools as _it
import operator as _op

from nose.tools import assert_equals, assert_raises

from ... import _util as _test

from wolfe.scheduler import _job

# pylint: disable = missing-docstring


def test_last_job_id():
    """ last_job_id returns the correct numbers """
    with _test.patched(_job, '_gen_id', _it.count(1).next):
        assert_equals(_job.last_job_id(), 0)
        assert_equals(_job.last_job_id(), 0)

    with _test.patched(_job, '_gen_id', _it.count(5).next) as gen_id:
        assert_equals(_job.last_job_id(), 4)

        assert_equals(gen_id(), 5)
        assert_equals(_job.last_job_id(), 5)
        assert_equals(_job.last_job_id(), 5)

        assert_equals(gen_id(), 6)
        assert_equals(_job.last_job_id(), 6)
        assert_equals(_job.last_job_id(), 6)


@_test.patch(_job, '_lock', name='lock')
def test_job_init(lock):
    """ Job properly initializes """
    lock.validate.side_effect = lambda x: list(x or ())

    job = _job.Job(2, "DESC", "GROUP", "LK", 3, 10, "EXTRA", [1], "ATT")

    assert_equals(job.__dict__, {
        'attempts': 'ATT',
        'desc': 'DESC',
        'extra': 'EXTRA',
        'group': 'GROUP',
        'id': 2,
        'importance': 3,
        'locks': ['L', 'K'],
        'locks_waiting': None,
        'not_before': 10,
        'predecessors': set([1]),
        'predecessors_waiting': None,
    })


@_test.patch(_job, '_lock')
def test_job_depend_on_error():
    """ Job.depend_on raises ValueError on invalid ID """
    job = _job.Job(3, "DESC", "GROUP", "LK", 3, 10, "EXTRA", [1, 2], "ATT")

    assert_equals(job.predecessors, set([1, 2]))
    with assert_raises(ValueError):
        job.depend_on("lala")
    with assert_raises(ValueError):
        job.depend_on(None)
    assert_equals(job.predecessors, set([1, 2]))


@_test.patch(_job, '_lock')
def test_job_depend_on_error2():
    """ Job.depend_on raises ValueError on ID outside the range """
    job = _job.Job(4, "DESC", "GROUP", "LK", 3, 10, "EXTRA", [1], "ATT")

    assert_equals(job.predecessors, set([1]))
    with assert_raises(ValueError):
        job.depend_on(-1)
    with assert_raises(ValueError):
        job.depend_on(0)
    with assert_raises(ValueError):
        job.depend_on(10)
    assert_equals(job.predecessors, set([1]))


@_test.patch(_job, '_lock')
def test_job_depend_on_ok():
    """ Job.depend_on accepts valid IDs and ignores dupes """
    job = _job.Job(4, "DESC", "GROUP", "LK", 3, 10, "EXTRA", [1], "ATT")

    assert_equals(job.predecessors, set([1]))
    job.depend_on(1)
    assert_equals(job.predecessors, set([1]))
    job.depend_on(2)
    assert_equals(job.predecessors, set([1, 2]))


@_test.patch(_job, 'Job', name='job_class')
@_test.patch(_job, '_gen_id', name='gen_id')
@_test.patch(_job, '_lock')
def test_job_from_todo(gen_id, job_class):
    """ job_from_todo properly initializes a job """
    gen_id.side_effect = [23]
    job_class.side_effect = lambda *x, **y: 'DOH'

    todo = _test.Bunch(
        desc="lalala", group="baz", locks=["foo", "bar"], importance=18,
        not_before=10
    )

    job = _job.job_from_todo(todo)

    assert_equals(job, "DOH")
    assert_equals(map(tuple, gen_id.mock_calls), [
        ('', (), {}),
    ])
    assert_equals(map(tuple, job_class.mock_calls), [(
        '', (23, 'lalala', 'baz', ['foo', 'bar'], 18, 10, {}, set([]), []), {}
    )])


@_test.patch(_job, 'job_from_todo', name='job_factory')
@_test.patch(_job, '_lock')
def test_joblist_from_todo_simple(job_factory):
    """ joblist_from_todo works in the trivial case """
    gen = _it.count(20).next
    job_factory.side_effect = lambda x: _test.Bunch(t=x, id=gen())

    todo = _test.Bunch(predecessors=lambda: (), successors=lambda: ())

    jobs = _job.joblist_from_todo(todo)

    assert_equals(map(_op.attrgetter('id', 't'), jobs), [(20, todo)])


@_test.patch(_job, 'job_from_todo', name='job_factory')
@_test.patch(_job, '_lock')
def test_joblist_from_todo_tree(job_factory):
    """ joblist_from_todo works for a simple tree """
    gen = _it.count(20).next

    class Depender(list):
        def __call__(self, value):
            self.append(value)

    class Todo(object):
        def __init__(self):
            self._succ = []

        def predecessors(self):  # pylint: disable = no-self-use
            return ()

        def successors(self):
            return self._succ

    job_factory.side_effect = lambda x: _test.Bunch(
        t=x, id=gen(), depend_on=Depender()
    )

    todo = Todo()
    todo2 = Todo()
    todo3 = Todo()
    todo4 = Todo()
    todo5 = Todo()

    todo.successors().append(todo2)
    todo.successors().append(todo4)
    todo2.successors().append(todo3)
    todo4.successors().append(todo5)

    jobs = _job.joblist_from_todo(todo)

    assert_equals(map(_op.attrgetter('id', 't', 'depend_on'), jobs), [
        (20, todo, []),
        (21, todo2, [20]),
        (22, todo4, [20]),
        (23, todo3, [21]),
        (24, todo5, [22]),
    ])


@_test.patch(_job, 'job_from_todo', name='job_factory')
@_test.patch(_job, '_lock')
def test_joblist_from_todo_dag(job_factory):
    """ joblist_from_todo works for a complex DAG """
    gen = _it.count(20).next

    class Depender(list):
        def __call__(self, value):
            self.append(value)

    class Todo(object):
        def __init__(self, *pre):
            self._succ = []
            self._pre = pre

        def predecessors(self):
            return self._pre

        def successors(self):
            return self._succ

    job_factory.side_effect = lambda x: _test.Bunch(
        t=x, id=gen(), depend_on=Depender()
    )

    todo = Todo(1, 2)
    todo2 = Todo(1, 3)
    todo3 = Todo(5, 8)
    todo4 = Todo()
    todo5 = Todo(3, 8, 13)

    todo.successors().append(todo2)
    todo.successors().append(todo4)
    todo2.successors().append(todo3)
    todo4.successors().append(todo5)
    todo.successors().append(todo5)
    todo2.successors().append(todo5)

    jobs = _job.joblist_from_todo(todo)

    assert_equals(map(_op.attrgetter('id', 't', 'depend_on'), jobs), [
        (20, todo, [1, 2]),
        (21, todo2, [1, 3, 20]),
        (22, todo4, [20]),
        (23, todo5, [3, 8, 13, 20, 21, 22]),
        (24, todo3, [5, 8, 21]),
    ])


@_test.patch(_job, 'job_from_todo', name='job_factory')
@_test.patch(_job, '_lock')
def test_joblist_from_todo_cycle(job_factory):
    """ joblist_from_todo detects cycles """
    gen = _it.count(20).next

    class Depender(list):
        def __call__(self, value):
            self.append(value)

    class Todo(object):
        def __init__(self, *pre):
            self._succ = []
            self._pre = pre

        def predecessors(self):
            return self._pre

        def successors(self):
            return self._succ

    job_factory.side_effect = lambda x: _test.Bunch(
        t=x, id=gen(), depend_on=Depender()
    )

    todo = Todo()
    todo.successors().append(todo)

    with assert_raises(_job.DependencyCycle):
        _job.joblist_from_todo(todo)

    todo = Todo(1, 2)
    todo2 = Todo(1, 3)
    todo3 = Todo(5, 8)
    todo4 = Todo()
    todo5 = Todo(3, 8, 13)

    todo.successors().append(todo2)
    todo.successors().append(todo4)
    todo2.successors().append(todo3)
    todo4.successors().append(todo5)
    todo.successors().append(todo5)
    todo2.successors().append(todo5)
    todo3.successors().append(todo)

    with assert_raises(_job.DependencyCycle) as e:
        _job.joblist_from_todo(todo)
    assert_equals(e.exception.args[0], [todo, todo2, todo3])
