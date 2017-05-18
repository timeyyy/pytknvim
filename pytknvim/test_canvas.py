
from tkinter import *

r = Tk()
c = Canvas(r)

c.pack()

_colsize = 20
_rowsize = 20

top = 0
bot = 10
left = 0
right = 10
c.configure(xscrollincrement=_rowsize)
colours = ['#000000', '#110000', '#220000', '#330000', '#440000',
           '#550000', '#660000', '#770000', '#880000', '#990000',
           '#AA0000']

cells= [[None for c in range(right+1)] for r in range(bot+1)]

for rownum in range(bot, top - 1, -1):
    for colnum in range(right, left - 1, -1):
        x1 = colnum * _colsize
        y1 = rownum * _rowsize
        x2 = (colnum + 1) * _colsize
        y2 = (rownum + 1) * _rowsize
        # for each cell, create two items: The rectangle is used for
        # filling background and the text is for cell contents.
        rect = c.create_rectangle(x1, y1, x2, y2, width=0, fill=colours[rownum])
        text = c.create_text(x1, y1, anchor='nw', width=1, text=' ')
        cells[rownum][colnum]=rect

rgn = c.bbox('all')
assert rgn

rect1 = cells[3][0]
rect2 = cells[bot - 2][right]
x1, y1, *_ = c.bbox(rect1)
x2, y2, *_ = c.bbox(rect2)
rgn = (x1, y1, x2, y2)
# rect = self.canvas.create_rectangle(x1, y1, x2, y2, width=0, fill='blue')

# c.configure(scrollregion=rgn)
# rect = c.create_rectangle(rgn, width=0, fill='blue')


def scrollset():
    c.configure(confine=False)
    c.configure(scrollregion=rgn)
    # c.create_rectangle(rgn, width=0, fill='blue')
    # c.yview_scroll(1, 'units')
def scroll():
    c.yview_scroll(1, 'units')
def scroll_up():
    c.yview_scroll(-1, 'units')

scrollset = Button(r, text='scroll region set', command=scrollset)
scrollset.pack()
scroll = Button(r, text='scroll down', command=scroll)
scroll.pack()
scroll_up = Button(r, text='scroll up', command=scroll_up)
scroll_up.pack()

r.mainloop()
