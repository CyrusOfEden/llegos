"""
Ray's async actors don't actually follow actor semantics of processing 1 message
at a time, leading to race conditions in state, which is not what we want.

This test is disabled until Ray makes their async actors actually actors,
otherwise they're just glorified classes.
"""

import time
from dataclasses import dataclass

import pytest
import ray


@pytest.fixture(scope="module")
def cluster():
    ray.init(num_cpus=1, num_gpus=0)
    yield ray
    ray.shutdown()


@ray.remote
@dataclass
class Worker:
    counter: float

    def modify(self, sleep_s: float):
        if self.counter % 2 == 0:
            self.counter /= 2
            time.sleep(sleep_s)
        else:
            time.sleep(sleep_s)
            self.counter = self.counter * 3 + 1
        return self.counter


@pytest.mark.asyncio
async def xtest_ray_actors():
    w = Worker.remote(counter=3)

    a = w.modify.remote(0.01)  # 3 • 3 + 1 = 10
    b = w.modify.remote(0.02)  # 10 / 2 = 5
    c = w.modify.remote(0.03)  # 3 • 5 + 1 = 16
    d = w.modify.remote(0.04)  # 16 / 2 = 8
    assert await a == 10
    assert await b == 5
    assert await c == 16
    assert await d == 8

    ray.kill(w)
