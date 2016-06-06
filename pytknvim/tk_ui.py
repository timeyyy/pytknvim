'''
Implements a UI for neovim  using tkinter.

* The widget has lines updated/deleted so that any
  given time it only contains what is being displayed.

* The widget is filled with spaces
'''

import sys
import math
import time
from neovim import attach

from tkquick.gui.tools import rate_limited

from pytknvim.ui_bridge import UIBridge
from pytknvim.screen import Screen
from pytknvim.util import _stringify_key, _stringify_color
from pytknvim.util import _split_color, _invert_color
from pytknvim.util import debug_echo
from pytknvim.util import attach_headless, attach_child
from pytknvim import tk_util

try:
    import Tkinter as tk
    import tkFont as tkfont
    import ttk
except ImportError:
    import tkinter as tk
    import tkinter.font as tkfont

import attr

RESIZE_DELAY = 0.04

def parse_tk_state(state):
    if state & 0x4:
        return 'Ctrl'
    elif state & 0x8:
        return 'Alt'
    elif state & 0x1:
        return 'Shift'


tk_modifiers = ('Alt_L', 'Alt_R',
                'Control_L', 'Control_R',
                'Shift_L', 'Shift_R',
                'Win_L', 'Win_R')


KEY_TABLE = {
    'slash': '/',
    'backslash': '\\',
    'asciicircumf': '^',
    'at': '@',
    'numbersign': '#',
    'dollar': '$',
    'percent': '%',
    'ampersand': '&',
    'asterisk': '*',
    'parenleft': '(',
    'parenright': ')',
    'underscore': '_',
    'plus': '+',
    'minus': '-',
    'bracketleft': '[',
    'bracketright': ']',
    'braceleft': '{',
    'braceright': '}',
    'quotedbl': '"',
    'apostrophe': "'",
    'less': "<",
    'greater': ">",
    'comma': ",",
    'period': ".",
    'BackSpace': 'BS',
    'Return': 'CR',
    'Escape': 'Esc',
    'Delete': 'Del',
    'Next': 'PageUp',
    'Prior': 'PageDown',
    'Enter': 'CR',
}


class MixTk():
    '''
    Tkinter actions we bind and use to communicate to neovim
    '''
    def tk_key_pressed(self,event, **k):
        keysym = event.keysym
        state = parse_tk_state(event.state)
        if event.char not in ('', ' ') \
                    and state in (None, 'Shift'):
            if event.keysym_num == ord(event.char):
                # Send through normal keys
                self._bridge.input(event.char)
                return
        if keysym in tk_modifiers:
            # We don't need to track the state of modifier bits
            return
        if keysym.startswith('KP_'):
            keysym = keysym[3:]

        # Translated so vim understands
        input_str = _stringify_key( KEY_TABLE.get(keysym, keysym), state)
        self._bridge.input(input_str)


    def _tk_quit(self, *args):
        self._bridge.exit()


    @rate_limited(1/RESIZE_DELAY, mode='kill')
    def _tk_resize(self, event):
        '''Let Neovim know we are changing size'''
        cols = int(math.floor(event.width / self._colsize))
        rows = int(math.floor(event.height / self._rowsize))
        if self._screen.columns == cols:
            if self._screen.rows == rows:
                return
        self.current_cols = cols
        self.current_rows = rows
        self._bridge.resize(cols, rows)
        if self.debug_echo:
            print('resizing c, r, w, h',
                    cols,rows, event.width, event.height)


    def bind_resize(self):
        '''
        after calling,
        widget changes will now be passed along to neovim
        '''
        print('binding resize to', self, self.text)
        self._configure_id = self.text.bind('<Configure>', self._tk_resize)


    def unbind_resize(self):
        '''
        after calling,
        widget size changes will not be passed along to nvim
        '''
        print('unbinding resize from', self)
        self.text.unbind('<Configure>', self._configure_id)


    def _get_row(self, screen_row):
        '''change a screen row to a tkinter row,
        defaults to screen.row'''
        if screen_row is None:
            screen_row = self._screen.row
        return screen_row + 1


    def _get_col(self, screen_col):
        '''change a screen col to a tkinter row,
        defaults to screen.col'''
        if screen_col is None:
            screen_col = self._screen.col
        return screen_col


    def tk_delete_line(self, screen_col=None, screen_row=None,
                                       del_eol=False, count=1):
        '''
        To specifiy where to start the delete from
        screen_col (defualts to screen.row)
        screen_row (defaults to screen.col)

        To delete the eol char aswell
        del_eol (defaults to False)

        count is the number of lines to delete
        '''
        line = self._get_row(screen_row)
        col = self._get_col(screen_col)
        start = "%d.%d" % (line, col)
        if del_eol:
            end = "%d.0" % (line + count)
        else:
            end = "%d.end" % (line + count - 1)
        self.text.delete(start, end)
        gotten = self.text.get(start, end)
        if self.debug_echo == True:
            print('deleted  from ' + start + ' to end ' +end)
            print('deleted '+repr(gotten))


    def tk_pad_line(self, screen_col=None, add_eol=False,
                                    screen_row=None, count=1):
        '''
        add required blank spaces at the end of the line
        can apply action to multiple rows py passing a count
        in
        '''
        line = self._get_row(screen_row)
        col = self._get_col(screen_col)
        for n in range(0, count):
            start = "%d.%d" % (line + n, col)
            spaces = " " * (self.current_cols - col)
            if add_eol:
                spaces += '\n'
            if self.debug_echo:
                pass
                # print('padding from ', start, ' with %d: '
                                                # % len(spaces))
                # print(repr(spaces))
            self.text.insert(start, spaces)


    def _start_blinking(self):
        # cursor is drawn seperatley in the window
        row, col = self._screen.row, self._screen.col
        text, attrs = self._screen.get_cursor()
        pos = "%d.%d" % (row +1, col)

        if not attrs:
            attrs = self._get_tk_attrs(None)
        fg = attrs[1].get('foreground')
        bg = attrs[1].get('background')
        try:
            self.text.stop_blink()
        except Exception:
            pass
        self.text.blink_cursor(pos, fg, bg)


class NvimHandler(MixTk):
    '''These methods get called by neovim'''

    def __init__(self, text, toplevel, address=-1, debug_echo=False):
        self.text = text
        self.toplevel = toplevel
        self.debug_echo = debug_echo

        self._insert_cursor = False
        self._screen = None
        self._foreground = -1
        self._background = -1
        self._pending = [0,0,0]
        self._attrs = {}
        self._reset_attrs_cache()
        self._colsize = None
        self._rowsize = None

        # Have we connected to an nvim instance?
        self.connected = False
        # Connecition Info for neovim
        self.address = address
        cols = 80
        rows = 24
        self.current_cols = cols
        self.current_rows = rows

        self._screen = Screen(cols, rows)
        self._bridge = UIBridge()

    @debug_echo
    def connect(self, *nvim_args, address=None, headless=False, exec_name='nvim'):
        # Value has been set, otherwise default to this functions default value
        if self.address != -1 and not address:
            address = self.address

        if headless:
            nvim = attach_headless(nvim_args, address)
        elif address:
            nvim = attach('socket', path=address, argv=nvim_args)
        else:
            nvim = attach_child(nvim_args=nvim_args, exec_name=exec_name)

        self._bridge.connect(nvim, self.text)
        self._screen = Screen(self.current_cols, self.current_rows)
        self._bridge.attach(self.current_cols, self.current_rows, rgb=True)
        bridge._call(bridge._nvim.request, "ui_set_popupmenu_external", True)
        self.connected = True
        self.text.nvim = nvim
        return nvim

    @debug_echo
    def _nvim_resize(self, cols, rows):
        '''Let neovim update tkinter when neovim changes size'''
        # TODO
        # Make sure it works when user changes font,
        # only can support mono font i think..
        self._screen = Screen(cols, rows)

    @debug_echo
    def _nvim_clear(self):
        '''
        wipe everyything, even the ~ and status bar
        '''
        self._screen.clear()

        self.tk_delete_line(del_eol=True,
                            screen_row=0,
                            screen_col=0,
                            count=self.current_rows)
        # Add spaces everywhere
        self.tk_pad_line(screen_row=0,
                         screen_col=0,
                         count=self.current_rows,
                         add_eol=True,)


    @debug_echo
    def _nvim_eol_clear(self):
        '''
        delete from index to end of line,
        fill with whitespace
        leave eol intact
        '''
        self._screen.eol_clear()
        self.tk_delete_line(del_eol=False)
        self.tk_pad_line(screen_col=self._screen.col,
                         add_eol=False)


    @debug_echo
    def _nvim_cursor_goto(self, row, col):
        '''Move gui cursor to position'''
        self._screen.cursor_goto(row, col)
        self.text.see("1.0")


    @debug_echo
    def _nvim_busy_start(self):
        self._busy = True


    @debug_echo
    def _nvim_busy_stop(self):
        self._busy = False


    @debug_echo
    def _nvim_mouse_on(self):
        self.mouse_enabled = True


    @debug_echo
    def _nvim_mouse_off(self):
        self.mouse_enabled = False


    @debug_echo
    def _nvim_mode_change(self, mode):
        self._insert_cursor = mode == 'insert'


    @debug_echo
    def _nvim_set_scroll_region(self, top, bot, left, right):
        self._screen.set_scroll_region(top, bot, left, right)


    @debug_echo
    def _nvim_scroll(self, count):
        self._flush()
        self._screen.scroll(count)
        abs_count = abs(count)
        # The minus 1 is because we want our tk_* functions
        # to operate on the row passed in
        delta = abs_count - 1
        # Down
        if count > 0:
            delete_row = self._screen.top
            pad_row = self._screen.bot - delta
        # Up
        else:
            delete_row = self._screen.bot - delta
            pad_row = self._screen.top

        self.tk_delete_line(screen_row=delete_row,
                            screen_col=0,
                            del_eol=True,
                            count=abs_count)
        self.tk_pad_line(screen_row=pad_row,
                         screen_col=0,
                         add_eol=True,
                         count=abs_count)
        # self.text.yview_scroll(count, 'units')


    # @debug_echo
    def _nvim_highlight_set(self, attrs):
        self._attrs = self._get_tk_attrs(attrs)


    # @debug_echo
    def _reset_attrs_cache(self):
        self._tk_text_cache = {}
        self._tk_attrs_cache = {}


    @debug_echo
    def _get_tk_attrs(self, attrs):
        key = tuple(sorted((k, v,) for k, v in (attrs or {}).items()))
        rv = self._tk_attrs_cache.get(key, None)
        if rv is None:
            fg = self._foreground if self._foreground != -1\
                                                else 0
            bg = self._background if self._background != -1\
                                                else 0xffffff
            n = {'foreground': _split_color(fg),
                'background': _split_color(bg),}
            if attrs:
                # make sure that fg and bg are assigned first
                for k in ['foreground', 'background']:
                    if k in attrs:
                        n[k] = _split_color(attrs[k])
                for k, v in attrs.items():
                    if k == 'reverse':
                        n['foreground'], n['background'] = \
                            n['background'], n['foreground']
                    elif k == 'italic':
                        n['slant'] = 'italic'
                    elif k == 'bold':
                        n['weight'] = 'bold'
                        # TODO
                        # if self._bold_spacing:
                            # n['letter_spacing'] \
                                    # = str(self._bold_spacing)
                    elif k == 'underline':
                        n['underline'] = '1'
            c = dict(n)
            c['foreground'] = _invert_color(*_split_color(fg))
            c['background'] = _invert_color(*_split_color(bg))
            c['foreground'] = _stringify_color(*c['foreground'])
            c['background'] = _stringify_color(*c['background'])
            n['foreground'] = _stringify_color(*n['foreground'])
            n['background'] = _stringify_color(*n['background'])
            # n = normal, c = cursor
            rv = (n, c)
            self._tk_attrs_cache[key] = (n, c)
        return rv


    # @debug_echo
    def _nvim_put(self, text):
        '''
        put a charachter into position, we only write the lines
        when a new row is being edited
        '''
        if self._screen.row != self._pending[0]:
            # write to screen if vim puts stuff on  a new line
            self._flush()

        self._screen.put(text, self._attrs)
        self._pending[1] = min(self._screen.col - 1,
                               self._pending[1])
        self._pending[2] = max(self._screen.col,
                               self._pending[2])


    # @debug_echo
    def _nvim_bell(self):
        pass


    # @debug_echo
    def _nvim_visual_bell(self):
        pass


    # @debug_echo
    def _nvim_update_fg(self, fg):
        self._foreground = fg
        self._reset_attrs_cache()
        foreground = self._get_tk_attrs(None)[0]['foreground']
        self.text.config(foreground=foreground)


    # @debug_echo
    def _nvim_update_bg(self, bg):
        self._background = bg
        self._reset_attrs_cache()
        background = self._get_tk_attrs(None)[0]['background']
        self.text.config(background=background)


    # @debug_echo
    def _nvim_update_suspend(self, arg):
        self.root.iconify()


    # @debug_echo
    def _nvim_set_title(self, title):
        self.root.title(title)


    # @debug_echo
    def _nvim_set_icon(self, icon):
        self._icon = tk.PhotoImage(file=icon)
        self.root.tk.call('wm', 'iconphoto',
                          self.root._w, self._icon)


    # @debug_echo
    def _flush(self):
        row, startcol, endcol = self._pending
        self._pending[0] = self._screen.row
        self._pending[1] = self._screen.col
        self._pending[2] = self._screen.col
        if startcol == endcol:
            #print('startcol is endcol return, row %s col %s'% (self._screen.row, self._screen.col))
            return
        ccol = startcol
        buf = []
        bold = False
        for _, col, text, attrs in self._screen.iter(row,
                                    row, startcol, endcol - 1):
            newbold = attrs and 'bold' in attrs[0]
            if newbold != bold or not text:
                if buf:
                    self._draw(row, ccol, buf)
                bold = newbold
                buf = [(text, attrs,)]
                ccol = col
            else:
                buf.append((text, attrs,))
        if buf:
            self._draw(row, ccol, buf)
        else:
            pass
            # print('flush with no draw')


    @debug_echo
    def _draw(self, row, col, data):
        '''
        updates a line :)
        '''
        for text, attrs in data:
            try:
                start = end
            except UnboundLocalError:
                start = "{}.{}".format(row + 1, col)
            end = start+'+{0}c'.format(len(text))

            if not attrs:
                attrs = self._get_tk_attrs(None)
            attrs = attrs[0]

            # if self.debug_echo:
                # print('replacing ', repr(self.text.get(start, end)))
                # print('with ', repr(text), ' at ', start, ' ',end)
            self.text.replace(start, end, text)

            if attrs:
                self.text.apply_attribute(attrs, start, end)
            start

    def _nvim_exit(self, arg):
        print('in exit')
        import pdb;pdb.set_trace()
        # self.root.destroy()

    @debug_echo
    def _nvim_update_sp(self, *args):
        pass

    def _nvim_popupmenu_show_items(self, items, sel):
        print('pum show', items)
        return
        self.text.pum_show(items, sel, self._screen.row,
                                        self._screen.col)

    # TODO TYPO in nvim event..
    def _nvim_popupmeny_select_item(self, num):
        print('pum sel')
        return
        self.text.pum_select(num)

    def _nvim_popupmenu_hide(self):
        print('pum hide')
        return
        self.text.pum_hide()

class NvimTk(tk_util.Text):
    '''namespace for neovim related methods,
    requests are generally prefixed with _tk_,
    responses are prefixed with _nvim_
    '''
    # we get keys, mouse movements inside tkinter, using binds,
    # These binds are handed off to neovim using _input

    # Neovim interpruts the actions and calls certain
    # functions which are defined and implemented in tk

    # So we can shutdown the neovim connections
    instances = []

    def __init__(self, parent, *_, address=False, toplevel=False, **kwargs):
        '''
        :parent: normal tkinter parent or master of the widget
        :toplevel: , if true will resize based off the toplevel etc
        :address: neovim connection info
            named pipe /tmp/nvim/1231
            tcp/ip socket 127.0.0.1:4444
            'child'
            'headless'
        :kwargs: config options for text widget
        '''
        tk_util.Text.__init__(self, parent, **kwargs)
        self.nvim_handler = NvimHandler(text=self,
                                        toplevel=toplevel,
                                        address=address,
                                        debug_echo=False)

        # TODO weak ref?
        NvimTk.instances.append(self)

    def _nvimtk_config(self, *args):
        '''required config'''
        # Hide tkinter cursor
        self.config(insertontime=0)

        # Remove Default Bindings and what happens on insert etc
        bindtags = list(self.bindtags())
        bindtags.remove("Text")
        self.bindtags(tuple(bindtags))

        self.bind('<Key>', self.nvim_handler.tk_key_pressed)

        self.bind('<Button-1>', lambda e: self.focus_set())

        # The negative number makes it pixels instead of point sizes
        size = self.make_font_size(13)
        self._fnormal = tkfont.Font(family='Monospace', size=size)
        self._fbold = tkfont.Font(family='Monospace', weight='bold', size=size)
        self._fitalic = tkfont.Font(family='Monospace', slant='italic', size=size)
        self._fbolditalic = tkfont.Font(family='Monospace', weight='bold',
                                 slant='italic', size=size)
        self.config(font=self._fnormal, wrap=tk.NONE)

        self.nvim_handler._colsize = self._fnormal.measure('M')
        self.nvim_handler._rowsize = self._fnormal.metrics('linespace')


    def nvim_connect(self, *a, **k):
        ''' force connection to neovim '''
        self.nvim_handler.connect(*a, **k)
        self._nvimtk_config()

    @staticmethod
    def kill_all():
        ''' Kill all the neovim connections '''
        raise NotImplementedError
        for self in NvimTk.instances:
            if self.nvim_handler.connected:
                # Function hangs us..
                # self.after(1, self.nvim_handler._bridge.exit)
                self.nvim_handler._bridge.exit()


    def pack(self, *arg, **kwarg):
        ''' connect to neovim if required'''
        tk_util.Text.pack(self, *arg, **kwarg)
        if not self.nvim_handler.connected:
            self.nvim_connect()

        self.nvim_handler.bind_resize()


    def grid(self, *arg, **kwarg):
        ''' connect to neovim if required'''
        tk_util.Text.grid(self, *arg, **kwarg)
        if not self.nvim_handler.connected:
            self.nvim_connect()

        self.nvim_handler.bind_resize()


    def schedule_screen_update(self, apply_updates):
        '''This function is called from the bridge,
           apply_updates calls the required nvim actions'''
        # if time.time() - self.start_time > 1:
            # print()
        # self.start_time = time.time()
        def do():
            apply_updates()
            self.nvim_handler._flush()
            self.nvim_handler._start_blinking()
        self.master.after_idle(do)


    def quit(self):
        ''' destroy the widget, called from the bridge'''
        self.after_idle(self.destroy)
