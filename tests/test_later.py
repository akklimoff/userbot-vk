import threading

from userbot.later import run_later


def test_actions_run_in_time_order_and_survive_a_failure():
    done, finished = [], threading.Event()

    def broken():
        raise RuntimeError("упало")

    run_later(0.05, lambda: (done.append("second"), finished.set()))
    run_later(0.02, broken)
    run_later(0.01, lambda: done.append("first"))
    assert finished.wait(2) and done == ["first", "second"]
    assert sum(thread.name == "later" for thread in threading.enumerate()) == 1
