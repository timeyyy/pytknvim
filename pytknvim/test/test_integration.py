'''
Neovim ui api is likely to change, also i do not understand really how and what it tries to do, it feels very granular and clunky. Makes it hard to do unit testing. Focuising on Integration testing...
'''

import os
import sys
import time
import _thread as thread
from subprocess import Popen, PIPE

import pytest
from neovim.ui.ui_bridge import UIBridge
from neovim.api import DecodeHook

from pytknvim.tk_ui import NvimTk
from pytknvim.util import attach_socket, attach_child, attach_headless
from pytknvim.test.util import compare_screens, send_tk_key
from pytknvim.util import rand_str

class MockNvimText(NvimTk):

    '''
    Our Nvim capable tkinter text widget
    '''


    def thread_ui(self):
        '''starts our us threaded so we can run tests'''
        named_pipe = '/tmp/nvim{0}'.format(rand_str(16))
        nvim = attach_headless(named_pipe)
        if sys.version_info[0] > 2:
            nvim = nvim.with_hook(DecodeHook())
        ui = self
        self._bridge = UIBridge()
        thread.start_new_thread(self._bridge.connect, (nvim, ui) )

        self.test_nvim = attach_headless(named_pipe)
        time.sleep(1)


class TestIntegration():


    def setup_class(cls):
        cls.nvimtk = MockNvimText()
        cls.nvimtk.thread_ui()
        # This one has to be used because of threads and locks
        cls.nvim = cls.nvimtk.test_nvim

    def teardown_class(cls):
        # Have to figure out how to teardown properlly 
        # Pipes still breaking...
        cls.nvimtk.quit()
        time.sleep(0.2)
        

    def teardown_method(self, method):
        '''delete everything so we get a clean slate'''
        self.send_tk_key('Esc')
        buf = self.nvimtk.test_nvim.buffers[0]
        buf[:] = [""]


    def send_tk_key(self, *keys):
        for key in keys:
            send_tk_key(self.nvimtk, key)


    def compare_screens(self):
        compare_screens(self.nvimtk)


    def test_load(self):
        self.compare_screens()


    def test_basic_insert(self):
        self.send_tk_key('i')
        self.compare_screens()
        self.send_tk_key('a')
        self.compare_screens()
        self.send_tk_key('b', 'c', 'd', 'e')
        self.compare_screens()

    def test_enter_key(self):
        self.send_tk_key('i')
        self.send_tk_key('b', 'c', 'd', 'e')
        self.send_tk_key('Enter')
        self.send_tk_key('Enter')
        self.compare_screens()
        self.send_tk_key('f', 'g', 'h')
        self.compare_screens()


