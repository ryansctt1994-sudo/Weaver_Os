import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from security_closure.boundary import Boundary, Request
from security_closure.run import CORPUS, run_case


@pytest.mark.parametrize("case", json.loads(CORPUS.read_text()), ids=lambda c: c["id"])
def test_frozen_attacks(case):
    run_case(case)


def test_concurrent_approval_has_one_effect(tmp_path):
    boundary = Boundary(tmp_path / "boundary.db")
    boundary.bootstrap()
    request = Request("agent", "increment", "counter", 1, "nonce")
    token = boundary.approve(request)
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda _: boundary.execute(request, token, "agent"), range(4)))
    assert outcomes.count("ACCEPT") == 1
    assert boundary.snapshot() == [("counter", 1)]
