"""Common code for graphical and text UIs."""
from neovim.compat import IS_PYTHON3


__all__ = ('Screen',)


if not IS_PYTHON3:
    range = xrange  # NOQA


class Cell(object):
    def __init__(self):
        self.text = ' '
        self.attrs = None

    def __repr__(self):
        return self.text

    def get(self):
        return self.text, self.attrs

    def set(self, text, attrs):
        self.text = text
        self.attrs = attrs

    def copy(self, other):
        other.text = self.text
        other.attrs = self.attrs

class DirtyState():
    '''
    Return information about cells that require updating
    '''
    def __init__(self):
        self.top = None
        self.left = None
        self.bot = None
        self.right = None

    def changed(self, top, left, bot, right):
        '''mark some section as being dirty'''
        if self.top == None:
            self.top = top
        else:
            self.top = min(self.top, top)
        if self.left == None:
            self.left = left
        else:
            self.left = min(self.left, left)
        if self.bot == None:
            self.bot = bot
        else:
            self.bot = max(self.bot, bot)
        if self.right == None:
            self.right = right
        else:
            self.right = max(self.right, right)

    def get(self):
        ''' get the areas that are dirty, call is_dirty first'''
        return self.top, self.left, self.bot, self.right

    def reset(self):
        '''mark the state as being not dirty'''
        self.top = None
        self.left = None
        self.bot = None
        self.right = None

    def is_dirty(self):
        if (self.top == None and self.bot == None
            and self.left == None and self.right == None):
            return False
        assert(self.top != None and self.left != None
               and self.bot != None and self.right != None)
        return True

class Attrs():
    def __init__(self):
        self.defaults = {}

    def set_default(self, k, v):
        self.defaults[k] = v

    def set_next(self, attrs):
        '''
        the next put will have these settings,
	Set the attributes that the next text put on the screen will have.
	`attrs` is a dict. Any absent key is reset to its default value.
        '''
        self.next = {}
        self.next['foreground'] = attrs.get('foreground', self.defaults.get('foreground'))
        self.next['background'] = attrs.get('background', self.defaults.get('background'))
        self.next['special'] = attrs.get('special', self.defaults.get('special'))
        self.next['reverse'] = attrs.get('reverse', False)
        self.next['italic'] = attrs.get('italic', False)
        self.next['bold'] = attrs.get('bold', False)
        self.next['underline'] = attrs.get('underline', False)
        self.next['undercurl'] = attrs.get('undercurl', False)

    def get_next(self):
        return self.next



class Screen(object):

    """Store nvim screen state."""

    def __init__(self, columns, rows):
        """Initialize the Screen instance."""
        self.columns = columns
        self.rows = rows
        self.row = 0
        self.col = 0
        self.top = 0
        self.bot = rows - 1
        self.left = 0
        self.right = columns - 1
        self._cells = [[Cell() for c in range(columns)] for r in range(rows)]
        self.attrs = Attrs()
        self._dirty = DirtyState()
        self._dirty.changed(self.top, self.left, self.bot, self.right)

    def clear(self):
        """Clear the screen."""
        self._clear_region(self.top, self.bot, self.left, self.right)

    def eol_clear(self):
        """Clear from the cursor position to the end of the scroll region."""
        self._clear_region(self.row, self.row, self.col, self.right)

    def cursor_goto(self, row, col):
        """Change the virtual cursor position."""
        self.row = row
        self.col = col

    def set_scroll_region(self, top, bot, left, right):
        """Change scroll region."""
        self.top = top
        self.bot = bot
        self.left = left
        self.right = right

    def scroll(self, count):
        """Shift scroll region."""
        top, bot = self.top, self.bot
        left, right = self.left, self.right
        if count > 0:
            start = top
            stop = bot - count + 1
            step = 1
        else:
            start = bot
            stop = top - count - 1
            step = -1
        # shift the cells
        for row in range(start, stop, step):
            target_row = self._cells[row]
            source_row = self._cells[row + count]
            for col in range(left, right + 1):
                tgt = target_row[col]
                source_row[col].copy(tgt)
        # clear invalid cells
        for row in range(stop, stop + count, step):
            self._clear_region(row, row, left, right)
        self._dirty.changed(top, left, bot, right)

    def put(self, text, attrs):
        """Put character on virtual cursor position."""
        cell = self._cells[self.row][self.col]
        cell.set(text, attrs)
        self._dirty.changed(self.row, self.col, self.row, self.col+1)
        self.cursor_goto(self.row, self.col + 1)

    def get_cell(self, row, col):
        """Get text, attrs at row, col."""
        return self._cells[row][col].get()

    def get_cursor(self):
        """Get text, attrs at the virtual cursor position."""
        return self.get_cell(self.row, self.col)

    def iter(self, startrow, endrow, startcol, endcol):
        """Extract text/attrs at row, startcol-endcol."""
        for row in range(startrow, endrow + 1):
            r = self._cells[row]
            cell = r[startcol]
            curcol = startcol
            attrs = cell.attrs
            buf = [cell.text]
            for col in range(startcol + 1, endcol + 1):
                cell = r[col]
                if cell.attrs != attrs or not cell.text:
                    yield row, curcol, ''.join(buf), attrs
                    attrs = cell.attrs
                    buf = [cell.text]
                    curcol = col
                    if not cell.text:
                        # glyph uses two cells, yield a separate entry
                        yield row, curcol, '', None
                        curcol += 1
                else:
                    buf.append(cell.text)
            if buf:
                yield row, curcol, ''.join(buf), attrs

    def _clear_region(self, top, bot, left, right):
        for rownum in range(top, bot + 1):
            row = self._cells[rownum]
            for colnum in range(left, right + 1):
                cell = row[colnum]
                cell.set(' ', None)
        self._dirty.changed(top, left, bot, right)
