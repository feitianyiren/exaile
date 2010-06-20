# Copyright (C) 2008-2010 Adam Olsen
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import logging
import gio
import gtk
import pango

from xl import (
    common,
    event,
    player,
    settings,
    providers
)
from xl.common import classproperty
from xl.formatter import TrackFormatter
from xl.nls import gettext as _
from xlgui import icons
from xlgui.widgets import rating, menu

logger = logging.getLogger(__name__)

class Column(gtk.TreeViewColumn):
    name = ''
    display = ''
    menu_title = classproperty(lambda c: c.display)
    renderer = gtk.CellRendererText
    formatter = classproperty(lambda c: TrackFormatter('$%s' % c.name))
    size = 10 # default size
    autoexpand = False # whether to expand to fit space in Autosize mode
    datatype = str
    dataproperty = 'text'
    cellproperties = {}

    def __init__(self, container, index):
        if self.__class__ == Column:
            raise NotImplementedError("Can't instantiate "
                "abstract class %s" % repr(self.__class__))

        self.container = container
        self.settings_width_name = "gui/col_width_%s" % self.name
        self.cellrenderer = self.renderer()
        self.extrasize = 0

        if index == 2:
            gtk.TreeViewColumn.__init__(self, self.display)
            icon_cellr = gtk.CellRendererPixbuf()
            # TODO: figure out why this returns the wrong value
            # and switch to it.
            #pbufsize = gtk.icon_size_lookup(gtk.ICON_SIZE_BUTTON)[0]
            pbufsize = icons.MANAGER.pixbuf_from_stock(gtk.STOCK_STOP).get_width()
            icon_cellr.set_fixed_size(pbufsize, pbufsize)
            icon_cellr.set_property('xalign', 0.0)
            self.extrasize = pbufsize
            self.pack_start(icon_cellr, False)
            self.pack_start(self.cellrenderer, True)
            self.set_attributes(icon_cellr, pixbuf=1)
            self.set_attributes(self.cellrenderer, **{self.dataproperty: index})
        else:
            gtk.TreeViewColumn.__init__(self, self.display, self.cellrenderer,
                **{self.dataproperty: index})
        self.set_cell_data_func(self.cellrenderer, self.data_func)

        try:
            self.cellrenderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        except TypeError: #cellrenderer doesn't do ellipsize - eg. rating
            pass

        for name, val in self.cellproperties.iteritems():
            self.cellrenderer.set_property(name, val)

        self.set_reorderable(True)
        self.set_clickable(True)
        self.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED) # needed for fixed-height mode
        self.set_sort_order(gtk.SORT_DESCENDING)

        # hack to allow button press events on the header to be detected
        self.set_widget(gtk.Label(self.display))

        self.connect('notify::width', self.on_width_changed)
        self.setup_sizing()

        event.add_callback(self.on_option_set, "gui_option_set")


    def on_option_set(self, typ, obj, data):
        if data == "gui/resizable_cols":
            self.setup_sizing()
        elif data == self.settings_width_name:
            self.setup_sizing()

    def on_width_changed(self, column, wid):
        if not self.container.button_pressed:
            return
        width = self.get_width()
        if width != settings.get_option(self.settings_width_name, -1):
            settings.set_option(self.settings_width_name, width)

    def setup_sizing(self):
        if settings.get_option('gui/resizable_cols', False):
            self.set_resizable(True)
            self.set_expand(False)
            width = settings.get_option(self.settings_width_name,
                    self.size+self.extrasize)
            self.set_fixed_width(width)
        else:
            self.set_resizable(False)
            if self.autoexpand:
                self.set_expand(True)
                self.set_fixed_width(1)
            else:
                self.set_expand(False)
                self.set_fixed_width(self.size+self.extrasize)

    def data_func(self, col, cell, model, iter):
        if type(cell) == gtk.CellRendererText:
            playlist = self.container.playlist

            if playlist is not player.QUEUE.current_playlist:
                return

            path = model.get_path(iter)
            track = model.get_value(iter, 0)

            if track == player.PLAYER.current and \
               path[0] == playlist.get_current_position():
                weight = pango.WEIGHT_HEAVY
            else:
                weight = pango.WEIGHT_NORMAL

            cell.props.weight = weight

            if -1 < playlist.spat_position < path[0]:
                cell.props.sensitive = False
            else:
                cell.props.sensitive = True

    def __repr__(self):
        return '%s(%s, %s, %s)' % (self.__class__.__name__,
            `self.name`, `self.display`, `self.size`)

class TrackNumberColumn(Column):
    name = 'tracknumber'
    #TRANSLATORS: Title of the track number column
    display = _('#')
    menu_title = _('Track Number')
    size = 30
    cellproperties = {'xalign': 1.0, 'width-chars': 4}
providers.register('playlist-columns', TrackNumberColumn)

class TitleColumn(Column):
    name = 'title'
    display = _('Title')
    size = 200
    autoexpand = True
providers.register('playlist-columns', TitleColumn)

class ArtistColumn(Column):
    name = 'artist'
    display = _('Artist')
    size = 150
    autoexpand = True
providers.register('playlist-columns', ArtistColumn)

class ComposerColumn(Column):
    name = 'composer'
    display = _('Composer')
    size = 150
    autoexpand = True
providers.register('playlist-columns', ComposerColumn)

class AlbumColumn(Column):
    name = 'album'
    display = _('Album')
    size = 150
    autoexpand = True
providers.register('playlist-columns', AlbumColumn)

class LengthColumn(Column):
    name = '__length'
    display = _('Length')
    size = 50
    cellproperties = {'xalign': 1.0}
providers.register('playlist-columns', LengthColumn)

class DiscNumberColumn(Column):
    name = 'discnumber'
    display = _('Disc')
    menu_title = _('Disc Number')
    size = 40
    cellproperties = {'xalign': 1.0, 'width-chars': 2}
providers.register('playlist-columns', DiscNumberColumn)

class RatingColumn(Column):
    name = '__rating'
    display = _('Rating')
    renderer = rating.RatingCellRenderer
    datatype = int
    dataproperty = 'rating'
    cellproperties = {'follow-state': False}

    def __init__(self, *args):
        Column.__init__(self, *args)
        self.cellrenderer.connect('rating-changed', self.on_rating_changed)
        self.saved_model = None

    def data_func(self, col, cell, model, iter):
        track = model.get_value(iter, 0)
        cell.props.rating = track.get_rating()
        self.saved_model = model

    def __get_size(self):
        """
            Retrieves the optimal size
        """
        size = icons.MANAGER.pixbuf_from_rating(0).get_width()
        size += 2 # FIXME: Find the source of this

        return size

    size = property(__get_size)

    def on_rating_changed(self, widget, path, rating):
        """
            Updates the rating of the selected track
        """
        iter = self.saved_model.get_iter(path)
        track = self.saved_model.get_value(iter, 0)
        oldrating = track.get_rating()

        if rating == oldrating:
            rating = 0

        track.set_rating(rating)
        maximum = settings.get_option('rating/maximum', 5)
        event.log_event('rating_changed', self, rating / maximum * 100)
providers.register('playlist-columns', RatingColumn)

class DateColumn(Column):
    name = 'date'
    display = _('Date')
    size = 50
providers.register('playlist-columns', DateColumn)

class GenreColumn(Column):
    name = 'genre'
    display = _('Genre')
    size = 100
    autoexpand = True
providers.register('playlist-columns', GenreColumn)

class BitrateColumn(Column):
    name = '__bitrate'
    display = _('Bitrate')
    size = 45
    cellproperties = {'xalign': 1.0}
providers.register('playlist-columns', BitrateColumn)

class IoLocColumn(Column):
    name = '__loc'
    display = _('Location')
    size = 200
    autoexpand = True
providers.register('playlist-columns', IoLocColumn)

class FilenameColumn(Column):
    name = 'filename'
    display = _('Filename')
    size = 200
    autoexpand = True
providers.register('playlist-columns', FilenameColumn)

class PlayCountColumn(Column):
    name = '__playcount'
    display = _('Playcount')
    size = 50
    cellproperties = {'xalign': 1.0}
providers.register('playlist-columns', PlayCountColumn)

class BPMColumn(Column):
    name = 'bpm'
    display = _('BPM')
    size = 50
    cellproperties = {'xalign': 1.0}
providers.register('playlist-columns', BPMColumn)

class LastPlayedColumn(Column):
    name = '__last_played'
    display = _('Last played')
    size = 10
providers.register('playlist-columns', LastPlayedColumn)

class ColumnMenuItem(menu.MenuItem):
    """
        A menu item dedicated to display the
        status of a column and change it
    """
    def __init__(self, column, after=None):
        """
            Sets up the menu item from a column description

            :param column: the playlist column
            :type column: :class:`Column`
            :param after: enumeration of menu
                items before this one
            :type after: list of strings
        """
        menu.MenuItem.__init__(self, column.name, self.factory, after)
        self.title = column.menu_title

    def factory(self, menu, parent_obj, parent_context):
        """
            Creates the menu item
        """
        item = gtk.CheckMenuItem(self.title)
        active = self.is_selected(self.name, parent_obj, parent_context)
        item.set_active(active)
        item.connect('activate', self.on_item_activate,
            self.name, parent_obj, parent_context)

        return item

    def is_selected(self, name, parent, context):
        """
            Returns whether a column is selected

            :rtype: bool
        """
        return name in settings.get_option('gui/columns')

    def on_item_activate(self, menu_item, name, parent_obj, parent_context):
        """
            Updates the columns setting
        """
        columns = settings.get_option('gui/columns')

        if name in columns:
            columns.remove(name)
        else:
            columns.append(name)

        settings.set_option('gui/columns', columns)

def __register_playlist_columns_menuitems():
    """
        Registers standard menu items for playlist columns
    """
    def is_column_selected(name, parent, context):
        """
            Returns whether a menu item should be checked
        """
        return name in settings.get_option('gui/columns')

    def is_resizable(name, parent, context):
        """
            Returns whether manual or automatic sizing is requested
        """
        resizable = settings.get_option('gui/resizable_cols', False)

        if name == 'resizable':
            return resizable
        elif name == 'autosize':
            return not resizable

    def on_column_item_activate(menu_item, name, parent_obj, parent_context):
        """
            Updates columns setting
        """
        columns = settings.get_option('gui/columns')

        if name in columns:
            columns.remove(name)
        else:
            columns.append(name)

        settings.set_option('gui/columns', columns)

    def on_sizing_item_activate(menu_item, name, parent_obj, parent_context):
        """
            Updates column sizing setting
        """
        if name == 'resizable':
            settings.set_option('gui/resizable_cols', True)
        elif name == 'autosize':
            settings.set_option('gui/resizable_cols', False)

    columns = ['tracknumber', 'title', 'artist', 'album',
               '__length', 'genre', '__rating', 'date']

    for provider in providers.get('playlist-columns'):
        if provider.name not in columns:
            columns += [provider.name]

    menu_items = []
    after = []

    for name in columns:
        column = providers.get_provider('playlist-columns', name)
        menu_item = ColumnMenuItem(column, after)
        menu_items += [menu_item]
        after = [menu_item.name]

    separator_item = menu.simple_separator('columns_separator', after)
    menu_items += [separator_item]
    after = [separator_item.name]

    sizing_item = menu.radio_menu_item('resizable', after, _('_Resizable'),
        'column-sizing', is_resizable, on_sizing_item_activate)
    menu_items += [sizing_item]
    after = [sizing_item.name]

    sizing_item = menu.radio_menu_item('autosize', after, _('_Autosize'),
        'column-sizing', is_resizable, on_sizing_item_activate)
    menu_items += [sizing_item]

    for menu_item in menu_items:
        providers.register('playlist-columns-menu', menu_item)
__register_playlist_columns_menuitems()
