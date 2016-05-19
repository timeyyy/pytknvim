'''
Implements a UI for neovim  using tkinter.

* The widget has lines updated/deleted so that any
  given time it only contains what is being displayed.

* The widget is filled with spaces to simplify moving
  the cursor around
'''
import sys
import math
import time

import neovim
from neovim_gui.ui_bridge import UIBridge
from neovim import attach
from neovim_gui.screen import Screen
from tkquick.gui.tools import rate_limited, delay_call

from pytknvim.util import _stringify_key, _stringify_color
from pytknvim.util import _split_color, _invert_color
from pytknvim.util import debug_echo
from pytknvim import tk_util

try:
    import Tkinter as tk
    import tkFont as tkfont
    import ttk
except ImportError:
    import tkinter as tk
    import tkinter.font as tkfont

from threading import Thread
from collections import deque
# import cProfile, pstats, StringIO

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
    '''Tkinter actions we bind and use to communicate to neovim'''
    def on_tk_select(self, arg):
        arg.widget.tag_remove('sel', '1.0', 'end')
        # TODO: this should change nvim visual range


    def _tk_key(self,event, **k):
        keysym = event.keysym
        state = event.state

        if event.char not in ('', ' '):
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
        input_str = _stringify_key(KEY_TABLE.get(keysym, keysym), state)
        self._bridge.input(input_str)


    def _tk_quit(self, *args):
        self._bridge.exit()


    def _tk_resize(self, event):
        '''Let Neovim know we are changing size'''
        if not self._screen:
            return
        cols = int(math.floor(event.width / self._colsize))
        rows = int(math.floor(event.height / self._rowsize))
        if self._screen.columns == cols and self._screen.rows == rows:
            return
        self.current_cols = cols
        self.current_rows = rows
        self._bridge.resize(cols, rows)
        # print('resizing c, r, w, h', cols,rows, event.width, event.height)
        #self.root.after_idle(lambda:self._bridge.resize(cols, rows))
        #time.sleep(1)


    def _clear_region(self, top, bot, left, right):
        '''
        Delete from top left to bottom right from the ui widget
        give screen coordinates in
        '''
        self._flush()
        start = "%d.%d" % (top+1, left)
        end = "%d.%d" % (bot+1, right+1)
        self.text.delete(start, end)
        # print('from {0} to {1}'.format(start, end))
        # print(repr('clear {0}'.format(self.text.get(start, end))))


    def bind_resize(self):
        '''
        after calling,
        widget changes will now be passed along to neovim
        '''
        self._configure_id = self.text.bind('<Configure>', self._tk_resize)


    def unbind_resize(self):
        '''
        after calling,
        widget size changes will not be passed along to nvim
        '''
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
            # + 1 spaces to keep cursor on same line..
            # TODO a bug in the cursor movement
            spaces = " " * (1 + self.current_cols - col)
            if not spaces:
                import pdb;pdb.set_trace()
            if add_eol:
                if not spaces:
                    spaces = ' \n'
                else:
                    spaces += '\n'
            if self.debug_echo:
                print('padding from ', start, ' with %d: '
                                                % len(spaces))
                print(repr(spaces))
            self.text.insert(start, spaces)


class MixNvim():


    '''These methods get called by neovim'''

    @delay_call(0.1)
    def _delayed_update(self):
        # update will be postponed by the above seconds each
        # time the function gets called
        self.unbind_resize()
        # REALLY SLOWS THINGS DOWN...
        self.text.master.update_idletasks()
        self.bind_resize()

    @debug_echo
    def _nvim_resize(self, cols, rows):
        '''Let neovim update tkinter when neovim changes size'''
        #Todo Check all the heights and so on are correct, :)
        # Make sure it works when user changes font,
        # only can support mono font i think..
        # also steal logic from gtk for faster updateing..
        self._screen = Screen(cols, rows)

        def resize():
            width = cols * self._colsize
            height = rows * self._rowsize
            self.unbind_resize()
            self.text.master.geometry('%dx%d' % (width, height))
            self.bind_resize()

        #print('resize', 'cols ',str(cols),'rows ',str(rows))
        self.root.after_idle(resize)
        self._delayed_update()
        #self.root.after_idle(self._delayed_nvim_resize, width, height)


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
        # self.text.mark_set(tk.INSERT, "{0}.{1}".format(
                        # self._screen.row+1, self._screen.col))


    @debug_echo
    def _nvim_cursor_goto(self, row, col):
        '''Move gui cursor to position'''
        # print('Moving cursor ', row,' ', col)
        self._screen.cursor_goto(row, col)
        self.text.mark_set(tk.INSERT, "{0}.{1}".
                                        format(row+1, col))
        self.text.see(tk.INSERT)


    def _nvim_busy_start(self):
        self._busy = True


    def _nvim_busy_stop(self):
        self._busy = False


    def _nvim_mouse_on(self):
        self.mouse_enabled = True


    def _nvim_mouse_off(self):
        '''er when is this fired?'''
        self.mouse_enabled = False


    def _nvim_mode_change(self, mode):
        self._insert_cursor = mode == 'insert'


    @debug_echo
    def _nvim_set_scroll_region(self, top, bot, left, right):
        self._screen.set_scroll_region(top, bot, left, right)


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


    @debug_echo
    def _nvim_highlight_set(self, attrs):
        # print('ATTRS', attrs)
        self._attrs = self._get_tk_attrs(attrs)


    def _reset_attrs_cache(self):
        self._tk_text_cache = {}
        self._tk_attrs_cache = {}


    def _get_tk_attrs(self, attrs):
        key = tuple(sorted((k, v,) for k, v in (attrs or {}).items()))
        rv = self._tk_attrs_cache.get(key, None)
        if rv is None:
            fg = self._foreground if self._foreground != -1 else 0
            bg = self._background if self._background != -1 else 0xffffff
            n = {'foreground': _split_color(fg),
                'background': _split_color(bg),}
            if attrs:
                # make sure that foreground and background are assigned first
                for k in ['foreground', 'background']:
                    if k in attrs:
                        n[k] = _split_color(attrs[k])
                for k, v in attrs.items():
                    if k == 'reverse':
                        n['foreground'], n['background'] = \
                            n['background'], n['foreground']
                    elif k == 'italic':
                        n['font_style'] = 'italic'
                    elif k == 'bold':
                        n['font_weight'] = 'bold'
                        # TODO
                        # if self._bold_spacing:
                            # n['letter_spacing'] = str(self._bold_spacing)
                    elif k == 'underline':
                        n['underline'] = 'solid'
            c = dict(n)
            c['foreground'] = _invert_color(*_split_color(fg))
            c['background'] = _invert_color(*_split_color(bg))
            c['foreground'] = _stringify_color(*c['foreground'])
            c['background'] = _stringify_color(*c['background'])
            n['foreground'] = _stringify_color(*n['foreground'])
            n['background'] = _stringify_color(*n['background'])
            n = ' '.join(['{0}="{1}"'.format(k, v) for k, v in n.items()])
            c = ' '.join(['{0}="{1}"'.format(k, v) for k, v in c.items()])
            rv = (n, c,)
            self._tk_attrs_cache[key] = rv
        return rv


    @debug_echo
    def _nvim_put(self, text):
        '''
        put a charachter into position, we only write the lines
        when a new row is being edited
        '''
        # print('put was called row %s col %s  text %s' % (self._screen.row, self._screen.col, text))
        if self._screen.row != self._pending[0]:
            # write to screen if vim puts stuff on  a new line
            print('calling flush from put')
            self._flush()

        self._screen.put(text, self._attrs)
        self._pending[1] = min(self._screen.col - 1, self._pending[1])
        self._pending[2] = max(self._screen.col, self._pending[2])


    def _nvim_bell(self):
        pass


    def _nvim_visual_bell(self):
        pass


    def _nvim_update_fg(self, fg):
        self._foreground = fg
        self._reset_attrs_cache()


    def _nvim_update_bg(self, bg):
        self._background = bg
        self._reset_attrs_cache()


    def _nvim_update_suspend(self, arg):
        self.root.iconify()


    def _nvim_set_title(self, title):
        self.root.title(title)


    def _nvim_set_icon(self, icon):
        self._icon = tk.PhotoImage(file=icon)
        self.root.tk.call('wm', 'iconphoto',
                          self.root._w, self._icon)


    def apply_attribute(self, widget, name, line, position):
        # Ensure the attribute name is associated with a tag configured with
        # the corresponding attribute format
        if name not in widget.added_tags:
            prefix = name[0:2]
            if prefix in ['fg', 'bg']:
                color = name[3:]
                if prefix == 'fg':
                    widget.tag_configure(name, foreground=color)
                else:
                    widget.tag_configure(name, background=color)
            widget.added_tags[name] = True
        # Now clear occurences of the tags in the current line
        ranges = widget.tag_ranges(name)
        for i in range(0, len(ranges), 2):
            start = ranges[i]
            stop = ranges[i+1]
            widget.tag_remove(start, stop)
        if isinstance(position, list):
            start = '%d.%d' % (line, position[0])
            end = '%d.%d' % (line, position[1])
            widget.tag_add(name, start, end)
        else:
            pos = '%d.%d' % (line, position)
            widget.tag_add(name, pos)


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
        # print('start row in flush is', row)
        for _, col, text, attrs in self._screen.iter(row, row, startcol,
                                                     endcol - 1):
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
        #sys.exit()


    def _draw(self, row, col, data, cr=None, cursor=False):
        '''
        updates a line :)
        '''
        assert len(data) == 1
        text, attrs = data[0]

        start = "{}.{}".format(row+1, col)
        end = start+'+{0}c'.format(len(text))
        self.text.replace(start, end, text)


    def _nvim_exit(self, arg):
        self.root.destroy()


class NvimTk(MixNvim, MixTk):
    '''
    Business Logic for making a tkinter neovim text widget

    we get keys, mouse movements inside tkinter, using binds,
    These binds are handed off to neovim using _input

    Neovim interpruts the actions and calls certain
    functions which are defined and implemented in tk

    The api from neovim does stuff line by line,
    so each callback from neovim produces a series
    of miniscule actions which in the end updates a line
    '''

    def __init__(self):
        # we destroy this when the layout changes
        self.start_time = time.time()
        self._insert_cursor = False
        self._screen = None
        self._foreground = -1
        self._background = -1
        self._pending = [0,0,0]
        self._attrs = {}
        self._reset_attrs_cache()

    def start(self, bridge):
        # MAXIMUM COLS AND ROWS AVALIABLE (UNTIL WE RESIZE THEN THIS CHANGES)
        self.current_cols = 80
        self.current_rows = 24
        bridge.attach(self.current_cols, self.current_rows, True)
        self._bridge = bridge
        self.debug_echo = True

        self.root = tk.Tk()
        self.root.protocol('WM_DELETE_WINDOW', self._tk_quit)
        text = tk_util.Text(self.root)
        self.text = text

        # Remove Default Bindings and what happens on insert etc
        bindtags = list(text.bindtags())
        bindtags.remove("Text")
        text.bindtags(tuple(bindtags))

        text.pack(expand=1, fill=tk.BOTH)
        text.focus_set()

        text.bind('<Key>', self._tk_key)
        self.bind_resize()

        # The negative number makes it pixels instead of point sizes
        self._fnormal = tkfont.Font(family='Monospace', size=12)
        self._fbold = tkfont.Font(family='Monospace', weight='bold', size=12)
        self._fitalic = tkfont.Font(family='Monospace', slant='italic', size=12)
        self._fbolditalic = tkfont.Font(family='Monospace', weight='bold',
                                 slant='italic', size=12)
        self.text.config(font=self._fnormal, wrap=tk.NONE)
        self._colsize = self._fnormal.measure('M')
        self._rowsize = self._fnormal.metrics('linespace')

        text.tag_configure('red', background='red')
        text.tag_configure('blue', background='blue')

        self.root.mainloop()

    def schedule_screen_update(self, apply_updates):
        '''This function is called from the bridge,
           apply_updates calls the required nvim actions'''
        # if time.time() - self.start_time > 1:
            # print()
        # self.start_time = time.time()
        def do():
            apply_updates()
            self._flush()
        self.root.after_idle(do)

    def quit(self):
        self.root.after_idle(self.root.quit)


class NvimFriendly(NvimTk):
    '''Meant to be subclassed so the user can tweak easily,
    atm im just using it to keep the config code seperate'''

    def __init__(self):
        super().__init__()

    def _nvim_mode_change(self, mode):
        self.text.config(
                        insertwidth=4,
                        insertontime=600,
                        insertofftime=150,
                        insertbackground='#21F221',
                        insertborderwidth=0)
        super()._nvim_mode_change(mode)
        if mode  == 'insert':
            pass
            #self.text.config(cursor='left_ptr')
        elif mode == 'normal':
            self.text.config(cursor='hand2')


def main(address=None):
    if address:
        nvim = attach('socket', path=address)
    else:
        try:
            address = sys.argv[1]
            nvim = attach('socket', path=address)
        except:
            nvim = attach('child', argv=['/usr/bin/nvim',
                                        '--embed',
                                        '-u',
                                        'NONE'])
    ui = NvimFriendly()
    bridge = UIBridge()
    bridge.connect(nvim, ui)
    if len(sys.argv) > 1:
        nvim.command('edit ' + sys.argv[1])

if __name__ == '__main__':
    main()
