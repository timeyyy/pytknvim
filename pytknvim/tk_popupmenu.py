import os
import tkinter as tk

import tkquick.gui.maker as maker
from tkquick.gui.style_defaults import *


grey = '#272822'
orange = '#FD971F'
green = '#A6E22E'
red = '#F92672'
blue = '#66D9EF'
class GuiListBox(maker.MakerScrolledList):

    def start(self):
        self.options = ''

    def finish(self):
        # Todo, center the text..http://stackoverflow.com/questions/17310034/tkinter-listbox-and-use-of-format

        self.listbox.config(selectmode='single',
                            activestyle='none')
        self.listbox.config(background=blue,
                            foreground=orange,
                            selectbackground=green,
                            selectforeground=red,
                            selectborderwidth=1,
                            font=TIMS_headingS,
                            borderwidth=3)
        self.c1=grey
        self.c2=grey
        self.styleList()

        self.config(relief='flat',
                    background=blue)
        # Remove Default bindings
        bindtags = list(self.listbox.bindtags())
        bindtags.remove('Listbox')
        self.listbox.bindtags(tuple(bindtags))

    def set_active(self, offset, start=None):
        if start is None:
            start = self.listbox.curselection()[0]
        selected = self.listbox.index(tk.ACTIVE)
        self.listbox.selection_clear(selected)
        self.listbox.see(start+offset)
        self.listbox.select_set(start + offset)
        self.listbox.activate(start + offset)


class GuiPum(maker.GuiMaker):
    def __init__(self, *a, **k):
        k['toplevel'] = True
        super().__init__(*a, **k)

    def start(self):
        ttk.Style().configure('blue.TFrame', background=blue)
        self.customFormStyle = {'style':'blue.TFrame'}
        self.customForm = [
            (GuiListBox, '', 'lb', cfg_gridA, {}),
            ]

    def finish(self):
        maker.center_window(self, 450, 250)
        self.custFrm.columnconfigure(0, weight=1)
        self.custFrm.rowconfigure(0, weight=1)
        lb = self.formRef['lb']
        lb.scrollbar.forget()
        self.overrideredirect(True)
        self.lb = lb


class PUM():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pum = GuiPum(self.master)
        self.pum_hide()
        self._pum_open = False
        self._temp_hide = False
        self.bind('<FocusOut>', self._pum_temp_hide)
        self.bind('<FocusIn>', self._pum_temp_show)

    def pum_show(self, items, sel, row, col):
        self._pum_open = True
        print('pum  show', items)
        self._pum.lb.listbox.delete(0, 'end')
        for i, item in enumerate(items):
            string = self._string_from_item(item)
            self._pum.lb.listbox.insert(i, string)
        if sel:
            self._pum.lb.set_active(sel, start=0)
        self._pum.attributes('-topmost', True)
        self._pum.attributes('-topmost', False)
        self._position_window(row, col)
        self.pum_select(sel)

    def pum_hide(self):
        self._pum_open = False
        self._temp_hide = False
        self._pum.withdraw()

    def pum_select(self, num):
        print('pum select')
        if num == -1:
            selected = self._pum.lb.listbox.index(tk.ACTIVE)
            self._pum.lb.listbox.selection_clear(selected)
        else:
            self._pum.lb.set_active(num, start=0)

    def _pum_temp_hide(self, event):
        if self._pum_open:
            self._temp_hide = True
            self._pum.withdraw()
        else:
            self._temp_hide = False

    def _pum_temp_show(self, event):
        if self._temp_hide and self._pum_open:
            self._pum.deiconify()
            # self._pum.attributes('-topmost', True)
            # elf._pum.attributes('-topmost', False)


    def _position_window(self, row, col):
        # Get width and height from widgeth
        # We have to draw the widget to get its dims,
        # Todo -> Best way is move ofscreen and draw..
        # Making Transparent as workaround
        # (may not work on some linux boxes)
        old_transparency = self._pum.attributes('-alpha')
        # TODO Transparency not working
        self._pum.attributes('-alpha', 0.5)
        self._pum.update_idletasks()
        self._pum.withdraw()
        width = self._pum.lb.listbox.winfo_reqwidth()
        height = self._pum.lb.listbox.winfo_reqheight()
        x, y = self._cur_position(row, col)
        self._pum.geometry('%dx%d+%d+%d' % (width, height, x, y))
        self._pum.attributes('-alpha', old_transparency)
        self._pum.deiconify()

    def _cur_position(self, row, col):
        # TODO assumes master is the toplevel
        abs_x = self.master.winfo_x()
        abs_y = self.master.winfo_y()
        rel_x, rel_y = self.bbox('%d.%d' % (row+1, col))[:2]
        return abs_x + rel_x, abs_y + rel_y

    def _string_from_item(self, item):
        return ''.join(item)
