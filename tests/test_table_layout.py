from rich.text import Text
from textual.app import App
from jellytui.models import Item
from jellytui.widgets.track_list import TrackList, column_widths


def test_content_widths_stay_compact_in_wide_terminal():
    labels = TrackList.COLUMN_LABELS
    rows = [tuple(Text(v) for v in ('', 'Planet of Destruction', 'Devilish Trio', 'Collection II', '03:10'))]
    widths = column_widths(labels, rows, 240)
    assert widths == [1, 21, 14, 13, 6]
    assert sum(widths) + 2 * len(labels) < 100


def test_long_metadata_caps_and_small_terminal_priority():
    rows = [tuple(Text(v) for v in ('', 'N' * 200, 'A' * 200, 'B' * 200, '123:45'))]
    wide = column_widths(TrackList.COLUMN_LABELS, rows, 240)
    assert wide == [1, 72, 40, 40, 6]
    small = column_widths(TrackList.COLUMN_LABELS, rows, 60)
    assert small[1] >= 20 and small[4] == 6
    assert small[1] > small[2] >= small[3]
    assert sum(small) + 10 <= 60


def test_two_columns_and_unicode_cell_width():
    rows = [(Text('界' * 14), Text('Artista'))]
    assert column_widths(('Nome', 'Artista / tipo'), rows, 200) == [28, 14]
    assert sum(column_widths(('Nome', 'Artista / tipo'), rows, 30)) + 4 <= 30


class TableApp(App):
    def compose(self):
        yield TrackList()


async def test_resize_ellipsis_and_values_are_preserved():
    app = TableApp()
    async with app.run_test(size=(220, 25)) as pilot:
        table = app.query_one(TrackList)
        items = [Item(str(i), 'Nome ' + '界' * 100, 'Audio', 'Artist ' * 30, 'Album ' * 30, 225) for i in range(50)]
        table.show_items(items, '3')
        table.move_cursor(row=3)
        await pilot.pause()
        assert [c.width for c in table.ordered_columns] == [1, 72, 40, 40, 6]
        assert not table.show_horizontal_scrollbar
        assert table.get_cell_at((0, 1)).plain == items[0].name
        assert '…' in '\n'.join(s.text for s in app.screen._compositor.render_strips())
        for width in (80, 45, 160):
            await pilot.resize_terminal(width, 25)
            await pilot.pause()
            assert table.selected is items[3]
            assert table.playing_id == '3' and table.row_count == 50
            assert sum(c.get_render_width(table) for c in table.ordered_columns) <= table.size.width
            assert table.ordered_columns[-1].width <= 6
            assert not table.show_horizontal_scrollbar
        table.show_items([Item('short', 'Short name', 'Audio', 'Artist', 'Album', 120)])
        await pilot.pause()
        assert [c.width for c in table.ordered_columns] == [1, 20, 14, 5, 6]


async def test_two_column_table_resize():
    class TwoColumns(TrackList):
        COLUMN_LABELS = ('Nome', 'Artista / tipo')
    class TwoColumnApp(App):
        def compose(self):
            yield TwoColumns()
    app = TwoColumnApp()
    async with app.run_test(size=(140, 25)) as pilot:
        table = app.query_one(TwoColumns)
        item = Item('artist', 'Artist name', 'MusicArtist')
        table.show_items([item])
        await pilot.pause()
        assert len(table.columns) == 2
        assert table.get_cell_at((0, 0)).plain == item.name
        assert [c.width for c in table.ordered_columns] == [20, 14]
        await pilot.resize_terminal(40, 25)
        assert table.selected is item
        assert not table.show_horizontal_scrollbar
