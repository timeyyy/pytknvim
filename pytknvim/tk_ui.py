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
from pprint import pprint

from tkquick.gui.tools import rate_limited

from pytknvim.ui_bridge import UIBridge
from pytknvim.screen import Screen
from pytknvim.util import _stringify_key, _stringify_color
from pytknvim.util import _split_color, _invert_color
from pytknvim.util import debug_echo
from pytknvim.util import attach_headless, attach_child
from pytknvim import tk_util

import tkinter as tk
import tkinter.font as tkfont

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
        if keysym == 'F5':
            def do(x, fill='red'):
                self.canvas.itemconfig(x, fill=fill)
            def gi(row=2, col=2):
                return self._screen._cells[self._screen.bot-row][col].canvas_data[1]
            import pdb;pdb.set_trace()
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

    # @rate_limited(1/RESIZE_DELAY, mode='kill')
    @debug_echo
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
        # print('binding resize to', self, self.canvas)
        self._configure_id = self.canvas.bind('<Configure>', self._tk_resize)


    def unbind_resize(self):
        '''
        after calling,
        widget size changes will not be passed along to nvim
        '''
        # print('unbinding resize from', self)
        self.canvas.unbind('<Configure>', self._configure_id)

    def _tk_draw_canvas(self, cols, rows):
        self._tk_fill_region(0, rows - 1, 0, cols - 1)


    # @debug_echo
    def _tk_fill_region(self, top, bot, left, right, delete=False):
        # create columns from right to left so the left columns have a
        # higher z-index than the right columns. This is required to
        # properly display characters that cross cell boundary

        # if delete:
        self._tk_destroy_region(top, bot, left, right)

        for rownum in range(bot, top - 1, -1):
            for colnum in range(right, left - 1, -1):
                x1 = colnum * self._colsize
                y1 = rownum * self._rowsize
                x2 = (colnum + 1) * self._colsize
                y2 = (rownum + 1) * self._rowsize
                # for each cell, create two items: The rectangle is used for
                # filling background and the text is for cell contents.
                rect = self.canvas.create_rectangle(x1, y1, x2, y2, width=0)
                text = self.canvas.create_text(x1, y1, anchor='nw', width=1, text=' ')
                cell = self._screen.get_cell(rownum, colnum)
                cell.set_canvas_data((rect, text))


    def _tk_clear_region(self, top, bot, left, right):
        attrs = self._screen.attrs.ui_cache.get(None)
        bg = attrs[1].get('background')

        self._tk_tag_region('clear', top, bot, left, right)
        self.canvas.itemconfig('clear', fill=bg)
        self.canvas.dtag('clear', 'clear')

    # @debug_echo
    def _tk_destroy_region(self, top, bot, left, right):
        self._tk_tag_region('destroy', top, bot, left, right)
        self.canvas.delete('destroy')
        self.canvas.dtag('destroy', 'destroy')

    def _tk_tag_region(self, tag, top, bot, left, right):
        x1, y1 = self._tk_get_coords(top, left)
        x2, y2 = self._tk_get_coords(bot, right)
        self.canvas.addtag_overlapping(tag, x1, y1, x2 + 1, y2 + 1)

    def _tk_get_coords(self, row, col):
        x = col * self._colsize
        y = row * self._rowsize
        return x, y


class NvimHandler(MixTk):
    '''These methods get called by neovim'''

    def __init__(self, canvas, toplevel, address=-1, debug_echo=False):
        self.canvas = canvas
        self.toplevel = toplevel
        self.debug_echo = debug_echo

        self._insert_cursor = False
        self._screen = None
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

        # The negative number makes it pixels instead of point sizes
        size = self.canvas.make_font_size(13)
        self._fnormal = tkfont.Font(family='Monospace', size=size)
        self._fbold = tkfont.Font(family='Monospace', weight='bold', size=size)
        self._fitalic = tkfont.Font(family='Monospace', slant='italic', size=size)
        self._fbolditalic = tkfont.Font(family='Monospace', weight='bold',
                                 slant='italic', size=size)
        # self.canvas.config(font=self._fnormal)
        self._colsize = self._fnormal.measure('M')
        self._rowsize = self._fnormal.metrics('linespace')
        self.canvas.configure(xscrollincrement=self._rowsize)

    # @debug_echo
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

        self._bridge.connect(nvim, self.canvas)
        self._screen = Screen(self.current_cols, self.current_rows)
        self._bridge.attach(self.current_cols, self.current_rows, rgb=True)
        # if len(sys.argv) > 1:
            # nvim.command('edit ' + sys.argv[1])
        self.connected = True
        self.canvas.nvim = nvim
        return nvim

    @debug_echo
    def _nvim_resize(self, cols, rows):
        '''Let neovim update tkinter when neovim changes size'''
        # TODO
        # Make sure it works when user changes font,
        # only can support mono font i think..
        # self._screen = Screen(cols, rows)
        self._screen.resize(cols, rows)
        self._tk_draw_canvas(cols, rows)

    # @debug_echo
    def _nvim_clear(self):
        '''
        wipe everyything, even the ~ and status bar
        '''
        self._screen.clear()

    # @debug_echo
    def _nvim_eol_clear(self):
        '''
        clear from cursor position to the end of the line
        '''
        self._screen.eol_clear()

    # @debug_echo
    def _nvim_cursor_goto(self, row, col):
        '''Move gui cursor to position'''
        self._screen.cursor_goto(row, col)

    # @debug_echo
    def _nvim_busy_start(self):
        self._busy = True

    def _nvim_busy_stop(self):
        self._busy = False

    def _nvim_mouse_on(self):
        self.mouse_enabled = True

    def _nvim_mouse_off(self):
        self.mouse_enabled = False

    # @debug_echo
    def _nvim_mode_change(self, mode):
        self._insert_cursor = mode == 'insert'

    @debug_echo
    def _nvim_set_scroll_region(self, top, bot, left, right):
        self._screen.set_scroll_region(top, bot, left, right)
        # x1 = left * self._colsize
        # y1 = top * self._rowsize
        # x2 = right * self._colsize
        # y2 = bot * self._rowsize
        rect1 = self._screen.get_cell(top, left).canvas_data[1]
        rect2 = self._screen.get_cell(bot - 1, right).canvas_data[1]
        x1, y1, *_ = self.canvas.bbox(rect1)
        x2, y2, *_ = self.canvas.bbox(rect2)
        rgn = (x1, y1, x2, y2)
        # self.canvas.configure(scrollregion=rgn)
        # rect = self.canvas.create_rectangle(x1, y1, x2, y2, width=0, fill='blue')

    @debug_echo
    def _nvim_scroll(self, count):
        self._screen.scroll(count)
        # return
        top = self._screen.top
        bot = self._screen.bot
        # left = self._screen.left
        # right = self._screen.right

        if count > 0:
            del_top = top
            del_bot = top + count - 1
            move_top = del_bot + 1
            move_bot = bot
            fill_top = move_bot -1 #+ count - 1
            fill_bot = fill_top + count
            clean_top = fill_top - 1
            clean_bot = fill_bot

            src_top, src_bot = top + count, bot
            dst_top, dst_bot = top, bot - count
            clr_top, clr_bot = dst_bot, src_bot
        else:
            del_top = bot + count + 1
            del_bot = bot
            move_top = top
            move_bot = del_top - 1
            fill_bot = move_top - 1
            fill_top = fill_bot + count + 1
            clean_top = fill_top
            clean_bot = fill_bot + 1

        # print(del_top, del_bot)
        # print(move_top, move_bot)
        # print(fill_top, fill_bot)
        self.canvas.yview_scroll(1, 'units')
        # self.canvas.yv

        # self._tk_tag_region('del', del_top, del_bot, self._screen.left, self._screen.right)
        # self.canvas.itemconfigure('del', fill='red')
        # self._tk_destroy_region(del_top, del_bot, self._screen.left, self._screen.right)
        # self._tk_tag_region('move', move_top, move_bot, self._screen.left, self._screen.right)
        # self.canvas.move('move', 0, -count * self._rowsize)
        # self.canvas.dtag('move', 'move')
        # self._tk_tag_region('fill', fill_top, fill_bot, self._screen.left, self._screen.right)
        # self.canvas.itemconfigure('fill', fill='green')
        # self._tk_tag_region('clean', clean_top, clean_bot, self._screen.left, self._screen.right)
        # self.canvas.itemconfigure('clean', fill='green')
        # self._tk_fill_region(clean_top, clean_bot, self._screen.left, self._screen.right)
        # self._screen._dirty.changed(clean_top, self._screen.left, clean_bot, self._screen.right)
        # self._screen._dirty.changed(top, self._screen.left, bot, self._screen.left + 3)
        self._screen._dirty.changed(self._screen.top, self._screen.left, self._screen.bot, self._screen.right)

    # @debug_echo
    def _nvim_highlight_set(self, attrs):
        self._screen.attrs.set_next(attrs)

    # @debug_echo
    def _nvim_put(self, text):
        '''
        put a charachter into position, we only write the lines
        when a new row is being edited
        '''
        self._screen.put(text)

    def _nvim_bell(self):
        pass

    def _nvim_visual_bell(self):
        pass

    # @debug_echo
    def _nvim_update_fg(self, fg):
        self._screen.attrs.set_default('foreground', fg)

    # @debug_echo
    def _nvim_update_bg(self, bg):
        self._screen.attrs.set_default('background', bg)

    # @debug_echo
    def _nvim_update_sp(self, sp):
        self._screen.attrs.set_default('special', sp)

    # @debug_echo
    def _nvim_update_suspend(self, arg):
        self.root.iconify()

    # @debug_echo
    def _nvim_set_title(self, title):
        self.root.title(title)

    # @debug_echo
    def _nvim_set_icon(self, icon):
        self._icon = tk.PhotoImage(file=icon)
        self.root.tk.call('wm', 'iconphoto', self.root._w, self._icon)

    # @debug_echo
    def _flush(self):
        if self._screen._dirty.is_dirty():
            print()
            print('dirty')
            print(self._screen._dirty.dirty_ranges)
            print()
            for top, left, bot, right in self._screen._dirty.get():
                # print('reparing ', '%s.%s' % (top, left), '%s.%s' % (bot, right))
                # print('max ', '%s.%s' % (self._screen.top, self._screen.left), '%s.%s' % (self._screen.bot, self._screen.right))
                for row, col, text, attrs in self._screen.iter(
                                            top, bot, left, right) :
                    # print('rep', row, col, text)
                    self._draw(row, col, text, attrs)
            self._screen._dirty.reset()


    # @debug_echo
    def _draw(self, row, col, data, attrs):
        '''
        updates a line :) from row,col to eol using attrs
        '''
        end = col + len(data)
        # print('_draw', row, col, repr(data))

        font = self._fnormal
        fg = attrs[0]['foreground']
        bg = attrs[0]['background']

        for i, c in enumerate(range(col, end)):
            cell = self._screen.get_cell(row, c)
            rect, text = cell.get_canvas_data()

            self.canvas.itemconfig(text, fill=fg, font=font, text=data[i])
            self.canvas.itemconfig(rect, fill=bg)


    # @debug_echo
    def _nvim_exit(self, arg):
        print('in exit')
        import pdb;pdb.set_trace()
        # self.root.destroy()



class NvimTk(tk_util.Canvas):
    '''namespace for neovim related methods,
    requests are generally prefixed with _tk_,
    responses are prefixed with _nvim_
    '''
    # we get keys, mouse movements inside tkinter, using binds,
    # These binds are handed off to neovim using _input

    # Neovim interpruts the actions and calls certain
    # functions which are defined and implemented in tk

    # The api from neovim does stuff line by line,
    # so each callback from neovim produces a series
    # of miniscule actions which in the end updates a line

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
        tk_util.Canvas.__init__(self, parent, **kwargs)
        self.nvim_handler = NvimHandler(canvas=self,
                                        toplevel=toplevel,
                                        address=address,
                                        debug_echo=True)

        # TODO weak ref?
        NvimTk.instances.append(self)

    def _nvimtk_config(self, *args):
        '''required config'''
        # Hide tkinter cursor
        # self.config(insertontime=0)

        # Remove Default Bindings and what happens on insert etc
        bindtags = list(self.bindtags())
        bindtags.remove("Canvas")
        self.bindtags(tuple(bindtags))

        self.bind('<Key>', self.nvim_handler.tk_key_pressed)

        self.bind('<Button-1>', lambda e: self.focus_set())



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
            if self.nvim_handler.debug_echo:
                print()
                print('Begin')
            apply_updates()
            self.nvim_handler._flush()
            if self.nvim_handler.debug_echo:
                print('End')
                print()
            # self.nvim_handler._start_blinking()
        self.master.after_idle(do)


    def quit(self):
        ''' destroy the widget, called from the bridge'''
        self.after_idle(self.destroy)
