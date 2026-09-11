import pytest
from jellytui.models import Item, Queue


def test_queue_boundaries_and_duplicates():
    queue = Queue()
    assert queue.move(1) is None
    tracks = [Item("a", "A", "Audio"), Item("a", "A", "Audio"), Item("b", "B", "Audio")]
    queue.replace(tracks, 1)
    assert queue.index == 1
    assert queue.move(1).name == "B"
    assert queue.move(1) is None and queue.index == 2
    assert queue.move(-1).name == "A"
    with pytest.raises(ValueError):
        queue.replace([Item("x", "Album", "MusicAlbum")], 0)
