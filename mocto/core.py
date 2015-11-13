#
# Copyright (C) 2015 by Artur Wroblewski <wrobell@pld-linux.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import asyncio
import itertools

import h5py
import n23

from .ws import create_app

def start(input=None, dashboard=None, data_dir=None, rotate=None):
    topic = n23.Topic()
    app = create_app(dashboard)
    app._topic = topic

    fin = h5py.File(input)

    files = None
    if data_dir:
        files = n23.data_logger_file('mocto', data_dir)

    w = n23.cycle(rotate, workflow, topic, fin, files=files)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(w)


def workflow(topic, fin, files=None):
    scheduler = n23.Scheduler(1)
    f = next(files) if files else None

    # for each sensor
    names = ['light', 'humidity']
    for name in names:
        data_log = n23.data_logger(f, name, 60) if f else None
        topic_send = broadcast(topic)
        consume = n23.split(topic_send, data_log)

        scheduler.add(name, replay(fin, name), consume)
    return scheduler()


@n23.coroutine
def broadcast(topic):
    while True:
        v1 = yield
        v2 = yield
        topic.put([v1, v2])


def replay(f, group_name):
    data = itertools.cycle(f[group_name + '/data'])
    return lambda: float(next(data)[0])

# vim: sw=4:et:ai
