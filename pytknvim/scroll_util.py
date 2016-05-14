from itertools import count
def compare_row(text_widget, screen, tk_row):
    '''
    returns false or true if a given row is the
    same or not

    the tkinter text widget must be padded with zeros?? 
    param:row -> starting from 0
    '''
    row = tk_row - 1

    end_col = text_widget.get_endcol(tk_row)
    for col in count(0):
        if end_col == col:
            return True
        screen_char = screen._cells[row][col].text
        tk_char = text_widget.get("%d.%d" % (tk_row, col))
        if tk_char != screen_char:
            return False
    else:
        return True

def insert_screen_row(tk_widget, screen, tk_row, endcol, draw):
    chars =  []
    row = tk_row - 1
    for col in range(0, endcol):
        # TODO tow -1 to row ?
        screen_char = screen._cells[row-1][col].text
        chars.append(screen_char)
    print('endrow ' + tk_widget.index('end-1c'))
    print('we want to insert into tkrow '+str(tk_row))
    text = ''.join(chars)
    text = '\n{0} '.format(text)
    start = "{}.0".format(tk_row)
    end = start+'+{0}c'.format(len(text)+1)
    tk_widget.insert(start, text)
    tk_widget.insert(end, ' \n')
    tk_widget.mark_set('insert', "{0}.{1}".format(tk_row, len(text)))
    # TODO
    # 'FUCK THE PROBLEM IS THE STATUS BAR
    # IT WILL GET SCROLLED WITH EVERYTHING

    # data = ''.join(chars)
    # print('DATA TO ADD is ' + data)
    # attrs = None
    # draw(tk_row, 0, ((data, attrs),))


    # tk_row = row + 1
    # text_widget.insert("%d.%d" % (tk_row, 0), '\n')
    # for col in range(0, endcol):
        # screen_char = screen._cells[row][col].text
        # text_widget.insert("%d.%d-1c" % (tk_row, col), screen_char)
    # text_widget.insert("%d.%d" % (tk_row, col+1), '\n')
    # print('len :' + str(text_widget.get_endcol))

