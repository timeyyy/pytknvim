from itertools import count
import time

from pytknvim.tk_ui import KEY_TABLE, _stringify_key

# TODO GET THIS DYNAMICALLY
STATUS_BAR_HEIGHT = 3


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
        all_rows.append(row)
    return all_rows


def _screen_rows(cells):
    '''get all rows of the internal screen '''
    for row in cells:
        line = []
        for char in row:
            line.append(char.text)
        yield ''.join(i for i in line)


def _remove_sidebar(line):
    '''remove the numbers and space if they are there'''
    found_numbers = False
    found_char = False
    for i, char in enumerate(line):
        if not found_numbers:
            try:
                int(char)
            except ValueError:
                if char != ' ':
                    found_char = True
                continue
            else:
                found_numbers = True
        else:
            try:
                int(char)
            except ValueError:
                break
            else:
                continue
    if found_numbers:
        if not found_char:
            return line[i+1:]
        else:
            raise Exception('chars where found in sidebar...',
                            line)
    else:
        return line


def _parse(lines, line_length, mock_inst, eol_trim):
    '''
    make the values for screen and tkinter text widget
    look like neovims values,
    neovim doesn't give us the ~ at the start,
    also remove our newline chars and end spacing
    also remove status bar stuff
    '''
    # Unfortunatley the code is a bit confusing
    # I thought the handling was more similar than
    # different for the two cases...
    file_name =  mock_inst.test_nvim.eval('expand("%:t")')
    side_bar = mock_inst.test_nvim.eval('&relativenumber') \
                        or mock_inst.test_nvim.eval('&number')
    all_rows = []
    for i, line in enumerate(lines):
        # screen doesn't have a \n
        if eol_trim:
            assert line[-eol_trim:] == '\n'
        try:
            assert len(line)-eol_trim  == line_length
        except AssertionError:
            # TODO does this line length need to match?
            if '-- INSERT --' not in line:
                raise
            break
        if side_bar:
            line = _remove_sidebar(line)
        if line[0] == '~':
            if eol_trim:
                parsed = line[1:-eol_trim].rstrip()
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

    # Remove the status bar (screen has a new line padded after)
    for i in range(1, 3):
        if '[No Name]' in all_rows[-i]:
            del all_rows[-i:]
            break
        elif file_name and file_name in all_rows[-i]:
            del all_rows[-i-1:]
            break
    else:
        raise Exception("couldn't find status bar...")
    return all_rows


def _parse_text(lines, line_length, mock_inst):
    return _parse(lines, line_length, mock_inst, eol_trim=1)


def _parse_screen(lines, line_length, mock_inst):
    return _parse(lines, line_length, mock_inst ,eol_trim=0)


def _check_scrolled(screen, nvim_rows, parsed_thing,
                    max_scroll):
    '''
    the screen and text widget only ever store
    what is being showed to the user,
    while neovim gives the entire buffer.

    we try matching slices of the lists to check
    if it has been scrolled
    checks max 10 scrolls forward and 10 backward
    '''
    viewable = len(parsed_thing)
    screen_size = screen.bot - screen.top
    if viewable != screen_size:
        maybe_status_bar = screen_size - viewable
        if maybe_status_bar > STATUS_BAR_HEIGHT:
            raise Exception('fix this...')
    for i in range(0, max_scroll + 1):
        end_index = i + viewable
        try:
            # CHECK IF SCROLLED DOWN
            assert nvim_rows[i:end_index] == parsed_thing
        except AssertionError:
            pass
        else:
            return True
        try:
            # CHECK IF SCROLLED UP
            assert nvim_rows[-end_index:-i] == parsed_thing
        except AssertionError:
            pass
        else:
            return True
    else:
        raise AssertionError('nvim rows did not match..\n \
                    make sure scroll amount is less than '
                    + str(max_scroll))


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

    parsed_text = _parse_text(text_rows, line_length, mock_inst)
    parsed_screen = _parse_screen(screen_rows, line_length,
                                  mock_inst)
    try:
        assert len(parsed_screen) == len(parsed_text)
    except:
        import pdb;pdb.set_trace()
    try:
        assert len(nvim_rows) == len(parsed_screen)
    # A scroll may have happend
    except AssertionError:
        _check_scrolled(mock_inst._screen,
                       nvim_rows,
                       parsed_text,
                       mock_inst.max_scroll)
        # TODO move this inside _check_scrolled
        # can use the offset to check all cells
        for sr, tr in zip(parsed_screen, parsed_text):
            assert sr == tr
    else:
        # No Scroll happened they should all match
        for sr, tr, nr in zip(parsed_screen,
                              parsed_text, nvim_rows):
            assert sr == tr == nr


class Event():
    def __init__(self, key, modifyer=None):
        '''
        mimics a tkinter key press event.
        this just fudges it enough so it passes the checks
        for our function...
        '''
        self.keysym = key
        self.char = key
        self.state = 0
        self.keycode = ord(key)
        self.keysym_num= ord(key)
        if modifyer:
            self.state = 1337
            self.keysym = modifyer.capitalize()


def send_tk_key(tknvim, key, modifyer=None):
    '''
    send a key through to our class as a tkinter event
    passed as tkinter or vim keys i.e Esc
    pass in a modifyer as, shift, alt, or ctrl
    '''
    assert modifyer in ('shift', 'alt', 'ctrl', None)
    if len(key) == 1:
        event = Event(key, modifyer)
        tknvim._tk_key(event)
    else:
        # Special key
        for value in KEY_TABLE.values():
            if value == key:
                break
        else:
            if key in KEY_TABLE:
                key = KEY_TABLE[key]
            else:
                raise KeyError(
                        'Please pass an acceptable key in')
        vimified = _stringify_key(key, [])
        tknvim._bridge.input(vimified)
    time.sleep(0.02)
