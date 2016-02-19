from __future__ import print_function
from future import standard_library
standard_library.install_aliases()

import sys
from pprint import pprint
import math

import neovim
from neovim.ui.ui_bridge import UIBridge
from neovim import attach
from neovim.ui.screen import Screen
#from tkquick.gui.tools import rate_limited, delay_call

import tk_util


try:
    import Tkinter as tk
    import tkFont as tkfont
except ImportError:
    import tkinter as tk
    import tkinter.font as tkfont

from threading import Thread
from collections import deque
# import cProfile, pstats, StringIO

tk_modifiers = ('Alt_L',        #tbd make this tuple
                'Alt_R', 
                'Control_L', 
                'Control_R', 
                'Shift_L', 
                'Shift_R',
                'Win_L',
                'Win_R')
                
KEY_TABLE = {
    'slash': '/',#
    'backslash': '\\',#
    'asciicircumf': '^',#
    'at': '@',#
    'numbersign': '#',#
    'dollar': '$',#
    'percent': '%',#
    'ampersand': '&',#ERROR IN GTK
    'asterisk': '*',#
    'parenleft': '(',#
    'parenright': ')',#
    'underscore': '_',#
    'plus': '+',#
    'minus': '-',#
    'bracketleft': '[',#
    'bracketright': ']',#
    'braceleft': '{',#ERROR IN GTK?
    'braceright': '}',#ERROR IN GTK?
    'quotedbl': '"',#
    'apostrophe': "'",#
    'less': "<",#
    'greater': ">",#
    'comma': ",",#
    'period': ".",#
    'BackSpace': 'BS',#
    'Return': 'CR',#
    'Escape': 'Esc',#
    'Delete': 'Del',#
    'Next': 'PageUp',#
    'Prior': 'PageDown',#
    'Enter': 'CR',
}

def _stringify_key(key, state):
    send = []
    if state:
        if 'Shift' in key:
            send.append('S')
        elif 'Ctrl' in key:
            send.append('C')
        elif 'Alt' in key:
            send.append('A')
    send.append(key)
    return '<' + '-'.join(send) + '>'

class MixTk():
    '''Tkinter actions we bind and use to communicate to neovim'''
    def on_tk_select(self, arg):
        arg.widget.tag_remove('sel', '1.0', 'end')
        # TODO: this should change nvim visual range


    def _tk_key(self,event, **k):
        self.text.tag_remove('red',"1.0")
        #self.text.tag_remove('blue', 'end')
        #self.text.highlight_pattern('\n', 'blue')
        self.text.highlight_pattern(' ', 'red')
        keysym = event.keysym
        state = event.state
        if event.char not in ('', ' '):
            #if not event.state:
            if event.keysym_num == ord(event.char):
                # Send through normal keys
                print('send normal key', event.char)
                self._bridge.input(event.char)
                return
        if keysym in tk_modifiers:
            # We don't need to track the state of modifier bits
            print('returning because of modifer')
            return
        if keysym.startswith('KP_'):
            keysym = keysym[3:]

        # Translated so vim understands
        input_str = _stringify_key(KEY_TABLE.get(keysym, keysym), state)
        print('sdenindg in a vim key', input_str)
        self._bridge.input(input_str)
    
    def _tk_quit(self, *args):
        self._bridge.exit()


    
    #@delay_call(1)
    def _tk_resize(self, event):
        '''Let Neovim know we are changing size'''
        cols = math.floor(event.width / self._cell_pixel_width)
        rows = math.floor(event.height / self._cell_pixel_height)
        self.current_cols = cols
        self.current_rows = rows
        self._bridge.resize(cols, rows)
        self._screen = Screen(cols, rows)
        self.root.after_idle(lambda:self._bridge.resize(cols, rows))
        print('resizing c, r, w, h', cols,rows, event.width, event.height)

    def _clear_region(self, top, bot, left, right):
        '''
        This is interesting.. maybe only for canvas?
        '''
        return
        print('top ',top,'  bot ', bot,' left ',left,' right ',right)
        self.text.delete("%d.%d" % (left, top),
                        "%d.%d" % (right, bot))

class MixNvim():


    '''These methods get called by neovim'''


    def _nvim_resize(self, cols, rows):
        '''Let neovim update tkinter when neovim changes size'''
        #Todo Check all the heights and so on are correct, :)
        # Make sure it works when user changes font,
        # only can support mono font i think..
        # also steal logic from gtk for faster updateing..
        width = cols * self._cell_pixel_width
        height = rows * self._cell_pixel_height
        def resize():
            self.text.master.geometry('%dx%d' % (width, height))
            #self.text.master.update_idletasks() REALLY SLOWS THINGS DOWN...

        print('resize', 'cols ',str(cols),'rows ',str(rows))
        #self._screen = Screen(cols, rows)
        self.root.after(1,resize)


    def _nvim_clear(self):
        '''erp?''' # same as gtk and for every case?
        print('CLEAR')
        #self.text.delete('1.0', 'end')
        #return
        self._clear_region(self._screen.top, self._screen.bot + 1,
                           self._screen.left, self._screen.right +1)
        self._screen.clear()


    def _nvim_eol_clear(self):
        '''delete from index to end of line and fill with whitespace...'''
        print('in eol col and row -> ', str(self._screen.col -1), str(self._screen.row))
        row, col = self._screen.row, self._screen.col
        self._clear_region(row, row + 1, col, self._screen.right + 1)
        self._screen.eol_clear()
        #row, col = self.text.get_pos()
        #self.text.delete("{0}.{1}".format(row, col),
                         #"{0}.{1}".format(row, self.current_cols))
        #self.text.insert(tk.INSERT, "".join(" " for i in range(self.current_cols - col)))
        return

        #print('EOL CLEAR from', "{0}.{1}".format(row, col), 'to ',"{0}.{1}".format(row, self.current_cols))


    def _nvim_cursor_goto(self, row, col):
        '''Move gui cursor to position'''
        # Tkinter row starts at 1 while col starts at 0
        self._screen.cursor_goto(row, col)
        #print('goto ','row ',str(row+1), ' col ', col)
        
        #self.text.mark_set(tk.INSERT, "%d.%d" % (row +1, col))

    def _nvim_busy_start(self):
        self._busy = True


    def _nvim_busy_stop(self):
        self._busy = False


    def _nvim_mouse_on(self):
        '''er when is this fired?'''
        self.mouse_enabled = True


    def _nvim_mouse_off(self):
        '''er when is this fired?'''
        self.mouse_enabled = False


    def _nvim_mode_change(self, mode):
        self._insert_cursor = mode == 'insert'


    def _nvim_set_scroll_region(self, top, bot, left, right):
        print('set scroll regione -> ')
        #self._screen.set_scroll_region(top, bot, left, right)
        print(top,bot,left,right)


    def _nvim_scroll(self, count):
        print('scroll count -> ',str(count))
        return
        col, row = self.text.index(tk.INSERT).split('.')
        move_to = int(col) + count
        print(col, move_to)
        self.text.yview(move_to)

        #top, bot, = self._screen.top, self._screen.bot + 1 
        #left, right, = self._screen.lefet, self._screen.right + 1 
        #if count > 0:


    def _nvim_highlight_set(self, attrs):
        print('highlight_set')
        # Apply attrs?
        if not attrs:
            return
        #key = tuple(sorted((k, v) for k, v in (attrs or {}).items()))
        print(attrs)
        #import pdb;pdb.set_trace()
        #self.on_nvim_update_line(attrs)


    def _nvim_put(self, text):
        '''
        NEOVIM
        put text into position, we have to also keep track of the
        cursors position manually i.e new lines etc
        neovim is working by sending us lines... so the line is deleted
        '''
        if self._screen.row != self._pending[0]:
            # flush pending text if jumped to a different row
            self._flush()
        # work around some redraw glitches that can happen
        #self._redraw_glitch_fix()
        # Update internal screen
        print('in put col and row -> ', str(self._screen.col -1), str(self._screen.row))
        print(text)
        self._screen.put(text, self._attrs)
        self._pending[1] = min(self._screen.col - 1, self._pending[1])
        self._pending[2] = max(self._screen.col, self._pending[2])
        return

        print('finished put')
        #if not self._insert_cursor:
            #status bar text???
            #print('throwing away ->', text)
            #return
        
        # Seems like i'm supposed to handle the put in lines... i don'tr really get it but i don't which means i need to clear more often
        # because i am putting the text down more often...
        self._nvim_eol_clear()
        print('putting -> ', repr(text), 'at ', self.text.index(tk.INSERT))
        pos = self.text.index(tk.INSERT)
        row, col = self.text.get_pos()
        # tkinter cols start at 0 while vim cols start at 1
        if col + 1 > self.current_cols:
            # Bump onto a new line
            #self.text.mark_set(tk.INSERT, "{0}.0".format(row+1))
            self.text.insert(pos, '\n')
            #for i in range(self.current_cols):
                #self.text.insert(' ')
            pos = self.text.index(tk.INSERT)

        # Insert text into position
        self.text.insert(pos, text)
        if row == 3:
            pass
            #import pdb;pdb.set_trace()


    def _nvim_bell(self):
        pass


    def _nvim_visual_bell(self):
        pass


    def _nvim_update_fg(self, arg):
        self.fg_color = arg


    def _nvim_update_bg(self, arg):
        self.bg_color = arg


    def _nvim_update_suspend(self, arg):
        self.root.iconify()


    def _nvim_set_title(self, title):
        self.root.title(title)


    def _nvim_set_icon(self, icon):
        self._icon = tk.PhotoImage(file=icon)
        self.root.tk.call('wm', 'iconphoto', self.root._w, self._icon)

    def on_nvim_layout(self, arg):
        print('NVIM LAYOUT')
        windows = {}
        # Recursion helper to build a tk frame graph from data received with
        # the layout event
        def build_widget_graph(parent, node, arrange='row'):
            widget = None
            if node['type'] in ['row', 'column']:
                widget = tk.Frame(parent)
            else:
                widget = tk.Text(parent, width=node['width'],
                              height=node['height'], state='normal',
                              font=self.font, exportselection=False,
                              fg=self.fg_color, bg=self.bg_color,
                              wrap='none', undo=False)
                setattr(widget, 'added_tags', {})
                # fill the widget one linefeed per row to simplify updating
                widget.insert('1.0', '\n' * node['height'])
                # We don't want the user to edit
                widget['state'] = 'disabled'
                windows[node['window_id']] = widget
            if 'children' in node:
                for child in node['children']:
                    build_widget_graph(widget, child, arrange=node['type'])
            if arrange == 'row':
                widget.pack(side=tk.LEFT, anchor=tk.NW)
            else:
                widget.pack(side=tk.TOP, anchor=tk.NW)
        
        # build the new toplevel frame
        toplevel = tk.Frame(self.root, takefocus=True)
        build_widget_graph(toplevel, arg)
        # destroy the existing one if exists
        if self.toplevel:
            self.toplevel.destroy()
        self.windows = windows
        self.toplevel = toplevel
        self.toplevel.pack()


    def on_nvim_delete_line(self, arg):
        widget = self.windows[arg['window_id']]
        line = arg['row'] + 1
        count = arg['count']
        startpos = '%d.0' % line
        endpos = '%d.0' % (line + count)
        widget['state'] = 'normal'
        # delete
        widget.delete(startpos, endpos)
        # insert at the end(they will be updated soon
        widget.insert('end', '\n' * count)
        widget['state'] = 'disabled'

    def on_nvim_win_end(self, arg):
        widget = self.windows[arg['window_id']]
        line = arg['row'] + 1
        endline = arg['endrow'] + 1
        marker = arg['marker']
        fill = arg['fill']
        startpos = '%d.0' % line
        endpos = '%d.0' % endline
        widget['state'] = 'normal'
        # delete
        widget.delete(startpos, endpos)
        line_fill = '%s%s\n' % (marker, fill * (widget['width'] - 1))
        # insert markers/fillers
        widget.insert('end', line_fill * (endline - line))
        widget['state'] = 'disabled'

    def on_nvim_update_line(self, arg):
        widget = self.text 
        pprint(arg)
        contents = ''.join(map(lambda c: c['content'], arg['line']))

        row = self.text.index(tk.INSERT).split('.')[1]
        startpos = '%d.0' % int(row) + 1
        endpos = '%d.end' % line
        #widget['state'] = 'normal'
        widget.delete(startpos, endpos)
        widget.insert(startpos, contents)
        #widget['state'] = 'disabled'
        if 'attributes' in arg:
            for name, positions in arg['attributes'].items():
                for position in positions:
                    self.apply_attribute(widget, name, line, position)

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
            return
        #self._cairo_context.save()
        ccol = startcol
        buf = []
        bold = False
        for _, col, text, attrs in self._screen.iter(row, row, startcol,
                                                     endcol - 1):
            newbold = attrs and 'bold' in attrs[0]
            if newbold != bold or not text:
                if buf:
                    self._pango_draw(row, ccol, buf)
                bold = newbold
                buf = [(text, attrs,)]
                ccol = col
            else:
                buf.append((text, attrs,))
        if buf:
            self._pango_draw(row, ccol, buf)
    

    def _pango_draw(self, row, col, data, cr=None, cursor=False):
        self.text.insert("row.col".format(row,col), data[0])
       # markup = []
       # for text, attrs in data:
       #     if not attrs:
                #attrs = self._get_pango_attrs(None)
            #attrs = attrs[1] if cursor else attrs[0]
            #markup.append('<span {0}>{1}</span>'.format(attrs, text))
        #markup = ''.join(markup)
        #self._pango_layout.set_markup(markup, -1)
        # Draw the text
        
        #if not cr:
            #cr = self._cairo_context
        #x, y = self._get_coords(row, col)
        #if cursor and self._insert_cursor:
            #cr.rectangle(x, y, self._cell_pixel_width / 4,
                         #self._cell_pixel_height)
            #cr.clip()
        #cr.move_to(x, y)
        #PangoCairo.update_layout(cr, self._pango_layout)
        #PangoCairo.show_layout(cr, self._pango_layout)
        #_, r = self._pango_layout.get_pixel_extents()


    def on_nvim_exit(self, arg):
        self.root.destroy()


class NvimTkUI(MixNvim, MixTk):
    def __init__(self):
        # we destroy this when the layout changes
        self.toplevel = None
        # windows_id -> text widget map
        self.windows = None
        # pending nvim events
        self.nvim_events = deque()
        self._insert_cursor = False

    def start(self, bridge):
        # MAXIMUM COLS AND ROWS AVALIABLE (UNTIL WE RESIZE THEN THIS CHANGES)
        self.current_cols = 80
        self.current_rows = 24
        bridge.attach(self.current_cols, self.current_rows, True)
        self._bridge = bridge

        self.root = tk.Tk()
        self.root.protocol('WM_DELETE_WINDOW', self._tk_quit)
        text = tk_util.Text(self.root)
        #text = tk.Text(self.root)
        self.text = text

        # Remove Default Bindings and what happens on insert etc
        bindtags = list(text.bindtags())
        bindtags.remove("Text")
        text.bindtags(tuple(bindtags))

        text.pack(expand=1, fill=tk.BOTH)
        text.focus_set()

        text.bind('<Key>', self._tk_key)
        text.bind('<Configure>', self._tk_resize)
        #text.bind(
        # The negative number makes it pixels instead of point sizes
        self.font = tkfont.Font(family='Monospace', size=-13)
        self._cell_pixel_width = self.font.measure('m')
        #TODO
        self._cell_pixel_height = 13 + 1.5 
        
        text.tag_configure('red', background='red')
        text.tag_configure('blue', background='blue')

        self.root.mainloop()

    def schedule_screen_update(self, apply_updates):
        '''This function is called from the bridge,
           apply_updates calls the required nvim actions'''
        def do():
            apply_updates()
        self.root.after_idle(apply_updates)

    def quit(self):
        self.root.after_idle(self.root.quit)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Need neovim listen address as argument')
    
    address = sys.argv[1]
    ui = NvimTkUI()

    #nvim = attach('child', argv=["/bin/env", 'nvim', '--embed'])
    nvim = attach('socket', path=address)
    if sys.version_info[0] > 2:
        from neovim.api import DecodeHook
        nvim = nvim.with_hook(DecodeHook())
    bridge = UIBridge()
    bridge.connect(nvim, ui)

'''
so we get keys, mouse movements inside tkinter, using binds,
These binds are handed off to neovim using _input

Neovim interpruts the actions and we get a function that we run in our mainloop, we implement the functions in our gui toolkit
'''
