from itertools import count
import time

class Unnest(Exception):
    '''Used to exit a nested loop'''
    pass

def _textwidget_rows(widget):
    '''Return all tkinter chars as rows'''
    # Rows start counting at 1 in tkinter text widget
    end_row, end_col = (int(i) for i in
                        widget.index('end-1c').split('.'))
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
    '''get all neovim rows'''
    all_rows = []
    for row in buff:
        all_rows.append(row.decode())
    return all_rows

def _screen_rows(cells):
    '''get all rows of the internal screen '''
    for row in cells:
        line = []
        for char in row:
            line.append(char.text)
        yield ''.join(i for i in line)

def _parse(lines, line_length, eol_trim):
    '''
    make the values for screen and tkinter text widget
    look like neovims values,
    neovim doesn't give us the ~ at the start,
    also remove our newline chars and end spacing
    also remove status bar stuff
    '''
    # Unfortunatley the corde is a bit confusing
    # I thought the handling was more similar than
    # different for the two cases...
    all_rows = []
    for i, line in enumerate(lines):
        # screen doesn't have a \n
        if eol_trim:
            assert line[-eol_trim:] == ' \n'
        try:
            assert len(line)-eol_trim  == line_length
        except AssertionError:
            # Todo does this line length need to match?
            if '-- INSERT --' not in line:
                raise
            break
        if line[0] == '~':
            if eol_trim: parsed = line[1:-eol_trim].rstrip()
            else:
                parsed = line[1:].rstrip()
            if not parsed: 
                # do not add blank lists
                continue
        else:
            if eol_trim:
                parsed = line[:-eol_trim].rstrip()
            else:
                parsed = line.rstrip()
            if not parsed:
                parsed = ''
        all_rows.append(parsed)
    
    # Remove the status bar (screen has a new line padded after)..
    for i in range(1, 3):
        if '[No Name]' in all_rows[-i]:
            del all_rows[-i:]
            break
    return all_rows


def _parse_text(lines, line_length):
    return _parse(lines, line_length, eol_trim=2)

def _parse_screen(lines, line_length):
    return _parse(lines, line_length, eol_trim=0)


def compare_screens(mock_inst):
    '''
    compares our text widget values with the nvim values.
    compares our internal screen with text widget

    nvim only makes the text (no spacing or newlines avaliable)
    
    '''
    line_length = mock_inst._screen.columns

    nvim_rows = _nvim_rows(mock_inst.test_nvim.buffers[0])
    text_rows = _textwidget_rows(mock_inst.text)
    screen_rows = _screen_rows(mock_inst._screen._cells)
    
    parsed_text = _parse_text(text_rows, line_length)
    parsed_screen = _parse_screen(screen_rows, line_length)
    assert len(nvim_rows) == len(parsed_text)
    assert len(parsed_text) == len(parsed_screen)

    for nr, tr, sr in zip(nvim_rows, parsed_text, screen_rows):
        assert tr == nr
        assert tr == sr

class Event():
    def __init__(self, key):
        '''
        mimics a tkinter key press event.
        this only works for normal key presses, no f1 or space etc
        '''
        if len(key) == 1:
            self.keysym = key
            self.char = key
            self.state = 0
            self.keycode = ord(key)
            self.keysym_num= ord(key)

def send_tk_key(tknvim, key):
    '''
    send a key through to our class as a tkinter event
    no modifyers as of yet, specia
    '''
    if len(key) == 1:
        event = Event(key)
        tknvim.__tk_key(event)
    else:
        for value in KEY_TABLE.values():
            if value == key:
                break
        else:
            if key in KEY_TABLE:
                key = KEY_TABLE[key]
            else:
                raise KeyError('Please pass an acceptable key in')
        tknvim._bridge.input(key)
    time.sleep(0.15)
    
    
