
import pytest

from pytknvim.screen import DirtyScreen
from pytknvim.screen import Screen


dscreen = DirtyScreen()

def assrt(screen, *values):
    assert list(dscreen.get()) == [*values]

def test_simple():
    dscreen.reset()
    dscreen.changed(1, 1, 1, 2)
    assrt(dscreen, (1, 1, 1, 2))

def test_second_range_added_after():
    dscreen.reset()
    dscreen.changed(1, 1, 1, 2)
    dscreen.changed(1, 3, 1, 5)
    assrt(dscreen, (1, 1, 1, 2), (1, 3, 1, 5))

def test_second_range_added_touching_previous():
    dscreen.reset()
    dscreen.changed(1, 1, 1, 2)
    dscreen.changed(1, 2, 1, 5)
    assrt(dscreen, (1, 1, 1, 5))

def test_second_range_added_before():
    dscreen.reset()
    dscreen.changed(1, 5, 1, 6)
    dscreen.changed(1, 2, 1, 3)
    assrt(dscreen, (1, 5, 1, 6), (1, 2, 1, 3))


# screen = Screen()
# def test_iter_works():
