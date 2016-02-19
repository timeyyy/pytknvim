import tkinter as tk
#import tkinter.ttk as tkk

class Text(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

    def get_pos(self, mark=tk.INSERT):
        '''returns row and column as an int'''
        return (int(x) for x in self.index(mark).split('.'))
   
    def highlight_pattern(self, pattern, tag, start="1.0", end="end",
                                     regexp=False):
       '''Apply the given tag to all text that matches the given pattern

       If 'regexp' is set to True, pattern will be treated as a regular
       expression according to Tcl's regular expression syntax.
       '''

       start = self.index(start)
       end = self.index(end)
       self.mark_set("matchStart", start)
       self.mark_set("matchEnd", start)
       self.mark_set("searchLimit", end)

       count = tk.IntVar()
       while True:
           index = self.search(pattern, "matchEnd","searchLimit", count=count, regexp=regexp)
           if index == "": break
           if count.get() == 0: break # degenerate pattern which matches zero-length strings
           self.mark_set("matchStart", index)
           self.mark_set("matchEnd", "%s+%sc" % (index, count.get()))
           self.tag_add(tag, "matchStart", "matchEnd")

    #def 
