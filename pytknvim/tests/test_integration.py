'''
Neovim ui api is likely to change,
also i do not understand really how and what it tries to do,
it feels very granular and clunky.
Makes it hard to do unit testing.
Focuising on Integration testing...
'''

import os
import time
import _thread as thread
import queue
from itertools import count
import tkinter as tk

import pytest

from pytknvim.tk_ui import NvimTk
from pytknvim.util import rand_str, attach_headless
from pytknvim.tests.util import compare_screens, send_tk_key
from pytknvim.tests.util import STATUS_BAR_HEIGHT, MAX_SCROLL, BUFFER_NUM


def threaded_nvimtk(address, out_queue):
    root = tk.Tk()
    text = NvimTk(root)
    text.nvim_connect('-u', 'NONE', headless=True, address=address)
    text.pack()

    out_queue.put(text)

    def quit():
        root.after_idle(root.quit)
    text.quit = quit
    root.mainloop()

def thread_ui():
    '''starts our us threaded so we can run tests
    this only works if we create the root in the same thread we
    call mainloop frome'''
    # scroll test will always check scrolling
    named_pipe = '/tmp/nvim{0}'.format(rand_str(16))
    out_queue = queue.Queue()
    thread.start_new_thread(threaded_nvimtk, (named_pipe, out_queue))
    nvimtk = out_queue.get(block=True)
    time.sleep(1)
    test_nvim = attach_headless(path=named_pipe)
    time.sleep(1)
    return nvimtk, test_nvim


class VimCommands():
    '''
    Just for readablility
    '''
    def v_insert_mode(self):
        self.send_tk_key('i')

    def v_normal_mode(self):
        self.send_tk_key('Esc')

    def v_back(self):
        self.v_normal_mode()
        self.send_tk_key('b')

    def v_delete_line(self):
        self.v_normal_mode()
        self.send_tk_key('d')
        self.send_tk_key('d')

    def v_up(self):
        self.v_normal_mode()
        self.send_tk_key('k')

    def v_down(self):
        self.v_normal_mode()
        self.send_tk_key('j')

    def v_undo(self):
        self.v_normal_mode()
        self.send_tk_key('u')

    def v_page_down(self):
        self.v_normal_mode()
        self.send_tk_key('G')

    def v_page_up(self):
        self.v_normal_mode()
        self.send_tk_key('g')
        self.send_tk_key('g')

    def v_jump(self, pos):
        self.v_normal_mode()
        self.send_tk_key(*"{}G".format(pos))
        self.send_tk_key('Enter')


class TestIntegration(VimCommands):

    def setup_class(cls):
        cls.nvimtk, cls.test_nvim = thread_ui()
        cls.nvimtk.test_nvim = cls.test_nvim
        cls.nvimtk._screen = cls.nvimtk.nvim_handler._screen
        cls.nvimtk.text = cls.nvimtk

        cls.nvimtk.max_scroll = MAX_SCROLL
        # This one has to be used because of threads and locks
        cls.nvim = cls.nvimtk.test_nvim
        # TODO Our compare_screen function doesn't work with number set
        cls.test_nvim.command("set nonumber")
        cls.test_nvim.command("set norelativenumber")
        cls.test_nvim.command("set noswapfile")

    def teardown_class(cls):
        cls.nvimtk.quit()
        time.sleep(0.2)

    def teardown_method(self, method):
        '''delete everything so we get a clean slate'''
        self.send_tk_key('Esc')
        buf = self.nvimtk.test_nvim.buffers[BUFFER_NUM]
        buf[:] = [""]


    def send_tk_key(self, *keys, modifyers=None):
        for key in keys:
            mod = None
            if type(key) in (tuple, list):
                key, mod = key
            send_tk_key(self.nvimtk, key, mod)

    def compare_screens(self):
        compare_screens(self.nvimtk)

    @pytest.mark.simple1
    def test_load(self):
        self.compare_screens()

    @pytest.mark.simple
    def test_basic_insert(self):
        self.v_insert_mode()
        self.compare_screens()
        self.send_tk_key('a')
        self.compare_screens()
        self.send_tk_key('b', 'c', 'd', 'e')
        self.compare_screens()


    @pytest.mark.simple
    def test_enter_key(self):
        self.v_insert_mode()
        self.send_tk_key('b', 'c', 'd', 'e')
        self.send_tk_key('Enter')
        self.send_tk_key('Enter')
        self.compare_screens()
        self.send_tk_key('f', 'g', 'h')
        self.compare_screens()
        self.v_back()
        self.v_insert_mode()
        self.send_tk_key('1','2','3')
        self.send_tk_key('Enter')
        self.compare_screens()


    @pytest.mark.simple
    def test_delete_line(self):
        self.v_insert_mode()
        self.send_tk_key('o', 'n', 'e')
        self.v_delete_line()
        self.compare_screens()
        self.v_insert_mode()
        self.send_tk_key('o', 'n', 'e')
        self.send_tk_key('Enter')
        self.send_tk_key('t', 'w', 'o')
        self.send_tk_key('Enter')
        self.send_tk_key('t', 'h', 'r', 'e', 'e')
        self.compare_screens()
        self.v_delete_line()
        self.compare_screens()
        self.v_undo()
        self.compare_screens()


    def test_o_and_shift_o(self):
        self.v_insert_mode()
        self.send_tk_key('1')
        self.v_normal_mode()
        # Open onto new line
        self.send_tk_key('o')
        self.send_tk_key('3')
        self.compare_screens()
        self.v_normal_mode()
        #  Open onto previous line
        self.send_tk_key('O')
        self.send_tk_key('2')
        self.compare_screens()
        # The end state of this tests should be
        # 1
        # 2
        #
        # 3


    # @nvimtester.register_test
    def test_scroll(self):
        # Force a scroll of an amount then compare_screens
        def _do(to_top):
            self.compare_screens()
            for i in range(0, to_top):
                self.v_up()
            self.compare_screens()
            for i in range(0, to_top):
                self.v_down()
            self.compare_screens()

        # TODO GET THIS DYNAMICALLY
        for i in count(1):
            self.v_page_down()
            self.v_insert_mode()
            scrolled = i\
                       - self.nvimtk.nvim_handler.current_rows\
                       + STATUS_BAR_HEIGHT
            self.send_tk_key(*str(i-1))
            self.send_tk_key('Enter')

            self.nvimtk.max_scroll = 50
            if scrolled in (1, 2, self.nvimtk.max_scroll):
                to_top = self.nvimtk.nvim_handler.current_rows + scrolled
                _do(to_top)
            if scrolled == self.nvimtk.max_scroll:
                break


    def test_page_up_down(self):
        def _do(to_top):
            self.compare_screens()
            self.v_page_up()
            self.compare_screens()
            self.v_page_down()
            self.compare_screens()

        for i in count(1):
            self.v_page_down()
            self.v_insert_mode()
            scrolled = i\
                       - self.nvimtk.nvim_handler.current_rows\
                       + STATUS_BAR_HEIGHT
            self.send_tk_key(*str(i-1))
            self.send_tk_key('Enter')

            # Make sure our last jump covers an entire page
            last_scroll = old_scroll = self.nvimtk.max_scroll
            if last_scroll < self.nvimtk.nvim_handler.current_rows:
                last_scroll = self.nvimtk.nvim_handler.current_rows + 1
                self.nvimtk.max_scroll = last_scroll

            if scrolled in (1, 2, last_scroll):
                to_top = self.nvimtk.nvim_handler.current_rows + scrolled
                time.sleep(1)
                _do(to_top)
            if scrolled == last_scroll:
                self.nvimtk.max_scroll = old_scroll
                break


    def test_big_file(self):
        '''
        doesn't test anything that our other tests doesn't,
        but just paves the way for testing a file
        '''
        test_file = os.path.join(os.path.dirname(__file__),
                                 'test_file')
        self.v_normal_mode()
        self.send_tk_key(*':e! '+test_file)
        self.send_tk_key('Enter')
        # Give time for actions to take place
        time.sleep(1)
        self.compare_screens()
        # TODO READ LEN OF FILE
        old_max = self.nvimtk.max_scroll
        self.nvimtk.max_scroll = 500
        self.v_page_down()
        time.sleep(0.5)
        self.compare_screens()
        self.v_page_up()
        time.sleep(0.5)
        self.compare_screens()
        self.nvimtk.max_sroll = old_max
        self.nvim.command('bwipeout')


    def test_number(self):
        to_test = ('load', 'basic_insert', 'enter_key')
        self.nvim.command("set nonumber")
        self.nvim.command("set relativenumber")
        time.sleep(0.5)
        for test in to_test:
            method = getattr(self, 'test_' + test)
            method()
            self.teardown_method(method)
