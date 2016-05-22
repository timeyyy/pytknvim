import os
import tkinter as tk


class TkBlink():
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blink_timer_id = None
        self._blink_status = 'off'
        self._blink_time = 500


    def _do_blink(self):
        if self._blink_status == 'off':
            self._blink_status = 'on'
            self.tag_add('cursorblock', self._blink_pos)
            self.tag_config('cursorblock',
                            background=self._blink_bg,
                            foreground=self._blink_fg)
        else:
            self.tag_delete('cursorblock')
            self._blink_status = 'off'

        self._blink_timer_id = self.after(self._blink_time,
                                          self._do_blink)


    def blink_cursor(self, pos, fg, bg):
        '''
        alternate the background color of the cursorblock tag
        self.blink_time = time inbetween blinks
        recall the function when pos/fg/bg change
        '''
        if self._blink_timer_id:
            self.after_cancel(self._blink_timer_id)
        self._blink_pos = pos
        self._blink_bg = bg
        self._blink_fg = fg
        self._do_blink()


    def stop_blink(self):
        '''remove cursor from screen'''
        self.after_cancel(self._blink_timer_id)
        self.tag_delete('cursorblock')
        self._blink_status = 'off'


class Text(TkBlink, tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._added_tags = {}

    def get_pos(self, row=None, col=None, mark=tk.INSERT):
        '''returns row and column as an int'''
        return (int(x) for x in self.index(mark).split('.'))


    def highlight_pattern(self, pattern, tag, start="1.0",
                          end="end", regexp=False):
       '''Apply the given tag to all text that matches the
       given pattern
       If 'regexp' is set to True, pattern will be treated as a
       regular expression according to Tcl's regular
       expression syntax.
       '''
       start = self.index(start)
       end = self.index(end)
       self.mark_set("matchStart", start)
       self.mark_set("matchEnd", start)
       self.mark_set("searchLimit", end)

       count = tk.IntVar()
       while True:
           index = self.search(pattern, "matchEnd","searchLimit",
                               count=count, regexp=regexp)
           if index == "":
               break
           # degenerate pattern which matches zero-length strings
           if count.get() == 0:
               break
           self.mark_set("matchStart", index)
           self.mark_set("matchEnd", "%s+%sc"
                                       % (index, count.get()))
           self.tag_add(tag, "matchStart", "matchEnd")


    def get_endcol(self, row):
        '''
        returns the index of the last char, not the newline char
        '''
        end_col = int(self.index(
                            str(row)+'.end-1c').split('.')[1])
        return end_col


    def apply_attribute(self, style, start, end):
        # Ensure the attribute name is associated with a tag
        # configured with the corresponding attribute format
        for name, existing_style in self._added_tags.items():
            # Style already exists
            if style == existing_style:
                break
        # Create a new
        else:
            name = self.make_name(style)
            self.font_from_style(name, style)
            self._added_tags[name] = style

        self.tag_add(name, start, end)


    def make_name(self, style):
        versions = [int(name[5:]) for name in \
                                        self._added_tags.keys()]
        return 'nvim_' + str(self.unique_int(versions))


    def font_from_style(self, name, style):
        '''configure font attributes'''
        # Get base font options
        new_font = tk.font.Font(self, self.cget("font"))
        for key, value in style.items():
            if key == 'size':
                if os.name == 'posix':
                    new_font.configure(size=int(value)-2)
                else:
                    new_font.configure(size=value)
            else:
                try:
                    eval('self.tag_configure(name, %s=value)'\
                                                        % key)
                except tk.TclError:
                    eval('new_font.configure(%s=value)' % key)
            self.tag_configure(name, font=new_font)
        return new_font


    @staticmethod
    def unique_int(values):
        '''
        if a list looks like 3,6
        if repeatedly called will return 1,2,4,5,7,8
        '''
        last = 0
        for num in values:
            if last not in values:
                break
            else:
                last += 1
        return last
