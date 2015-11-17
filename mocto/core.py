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
import functools
import itertools
import logging

import h5py
import n23

from .ws import create_app

logger = logging.getLogger(__name__)


def start(device, dashboard=None, data_dir=None, rotate=None, channel=None,
        replay=None):

    topic = n23.Topic()
    if dashboard:
        create_app(topic, dashboard)

    files = None
    if data_dir:
        files = n23.data_logger_file('mocto', data_dir)

    w = n23.cycle(
        rotate, workflow, topic, device, files=files, channel=channel,
        replay=replay
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(w)


def workflow(topic, device, files=None, channel=None, replay=None):
    scheduler = n23.Scheduler(1, timeout=0.25)
    fout = next(files) if files else None

    if replay:
        logger.info('replaying a data file {}'.format(replay))
        fin = h5py.File(replay)

        # for each sensor
        names = ['light', 'humidity']
        for name in names:
            data_log = n23.data_logger(fout, name, 60) if fout else None
            consume = n23.split(topic.put_nowait, data_log)
            scheduler.add(name, replay_file(fin, name), consume)
    else:
        raise ValueError('Reading from a device not supported yet')

    tasks = [scheduler()]
    if channel:
        p = publish(topic, channel)
        tasks.append(p)
        logger.info('publish data to redis channel {}'.format(channel))

    return asyncio.gather(*tasks)


def replay_file(f, group_name):
    data = itertools.cycle(f[group_name + '/data'])
    return lambda: float(next(data)[0])


@asyncio.coroutine
def publish(topic, name):
    import aioredis
    client = yield from aioredis.create_redis(('localhost', 6379))
    if __debug__:
        logger.debug('connected to redis server')
    while True:
        values = yield from topic.get()
        for v in values:
            client.publish_json(name, v._asdict())


# vim: sw=4:et:ai
