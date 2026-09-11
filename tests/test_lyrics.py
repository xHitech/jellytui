import pytest
from jellytui.lyrics import parse_lrc, Lyrics, LyricLine


def test_lrc_timestamps_multiple_fraction_and_sort():
    lyrics = parse_lrc("\ufeff[ar:Artist]\n[00:17.80]B\n[00:12.34][01:02.003]A\n[00:00]Intro\n[01:70]inválido")
    assert [(l.start, l.text) for l in lyrics.lines] == [(0, "Intro"), (12.34, "A"), (17.8, "B"), (62.003, "A")]


def test_lrc_offset_and_simultaneous_lines():
    lyrics = parse_lrc("[offset:500]\n[00:10.00]A\n[00:10.00]Tradução\n[00:12.00]")
    assert lyrics.lines == [LyricLine(9.5, "A / Tradução"), LyricLine(11.5, "")]
    assert lyrics.index_at(9.49) == -1
    assert lyrics.index_at(9.5) == 0


@pytest.mark.parametrize("position,expected", [(0, -1), (12.33, -1), (12.34, 0), (17.8, 1), (90, 1), (13, 0)])
def test_selection_and_backward_seek(position, expected):
    assert parse_lrc("[00:12.34]A\n[00:17.80]B").index_at(position) == expected


def test_jellyfin_ticks_and_missing_metadata():
    lyrics = Lyrics.from_jellyfin({"Metadata": {}, "Lyrics": [{"Text": "A", "Start": 69400000}, {"Text": "B", "Start": 120400000}]})
    assert lyrics.starts == [6.94, 12.04]
    assert lyrics.index_at(12.04) == 1


def test_unsynced_and_missing():
    assert not Lyrics.from_jellyfin({}).lines
    assert Lyrics.from_jellyfin({"Lyrics": [{"Text": "Unsynced"}]}).plain == ["Unsynced"]
    assert parse_lrc("Plain text\nSecond line").plain == ["Plain text", "Second line"]
