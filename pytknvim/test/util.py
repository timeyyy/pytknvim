from itertools import count
import time

class Unnest(Exception):
    '''Used to exit a nested loop'''
    pass

def _textwidget_rows(widget):
    '''Return all tkinter chars as rows'''
    # Rows start counting at 1 in tkinter text widget
    end_row, end_col = (int(i) for i in widget.index('end').split('.'))
    #end is the first garbage value'
    #end_col = end_col - 1 
    #if end_col == -1:
        # have to go back to end of last line..
    #    end_row == 
    try:
        for row in count(1):
            line = [] 
            for col in count(0):
                # Exit out
                if end_row == row:
                   if end_col == col:
                       raise Unnest
                # Add if not on new line
                char = widget.get('{0}.{1}'.format(row,col))
                line.append(char)
                if char == '\n':
                    yield ''.join(i for i in line)
                    break
    except Unnest:
        pass

           
def _nvim_rows(buff):
    all_rows = []
    for row in buff:
        all_rows.append(row.decode())
    return all_rows

def _screen_rows(cells):
    all_rows = []
    for row in cells:
        line = []
        for char in row:
            line.append(char.text)
        all_rows.append(''.join(i for i in line))
    return all_rows

def _parse_text(lines, line_length):
    '''
    make the text ouput look like neovim,
    remove ~ from start
    remove end of line and spacing on the right
    remove status bar stuff

    we have to pad with spaces until the end of the column, then we add a space and a newline

    the padding is required to be able to goto that position.
    the space new line is important otherwise the cursor goes
    down onto new line..
    '''
    all_rows = []
    for i, line in enumerate(lines):
        try:
            assert line[-2:] == ' \n'
        except AssertionError:
            # the file name if none set [No Name]
            if all_rows[-1][0] != '[No': 
                raise
            break
        try:
            assert len(line)-2  == line_length
        except AssertionError:
            if line != '-- INSERT -- \n':
                raise
            break
        # we cannot test with adding ~ at first col otherwise this will fail
        if line[0] == '~':
            parsed = line[1:-2].rsplit()
            import pdb;pdb.set_trace()# NEED TO MAKE TEXT DEL THE FIRST ~ on load... fuck me how?
            if not parsed: 
                # do not add blanks that are squiggles
                continue
        else:
            parsed = line[:-2].rsplit()
            if not parsed:
                parsed = ''
        all_rows.append(parsed)
    

    # Remove the status bar
    if '-- INSERT -- \n' == all_rows[-2]:
        del all_rows[-2:]
    else:
        del all_rows[-1:]
    return all_rows

#def _parsed_screen():
    #all_rows = []


def compare_screens(mock_inst):
    '''
    compares our text widget values with the nvim values.
    compares our internal screen with text widget

    nvim only makes the text (no spacing or newlines avaliable)
    
    '''
    nvim_rows = _nvim_rows(mock_inst.test_nvim.buffers[0])
    text_rows = _textwidget_rows(mock_inst.text)
    screen_rows = _screen_rows(mock_inst._screen._cells)
    
    parsed_text = _parse_text(text_rows,
                             line_length=mock_inst._screen.columns)
    import pdb;pdb.set_trace()
    #parsed_screen = _parse_screen(screen_rows)
    assert len(nvim_rows) == len(parsed_text)
    assert len(parsed_text) == len(screen_rows)

    for nr, tr, sr in zip(nvim_rows, parsed_text, screen_rows):
        assert tr == nr
        assert tr == sr

class Event():
    def __init__(self, key):
        '''
        this only works for normal key presses, no f1 or space etc
        '''
        self.keysym = key
        self.char = key
        self.state = 0
        self.keycode = ord(key)
        self.keysym_num= ord(key)

def send_tk_key(tknvim, key):
    '''
    send a normal key through to our class as a tkinter event
    '''
    event = Event(key)
    tknvim.__tk_key(event)
    time.sleep(0.5)
    
    
