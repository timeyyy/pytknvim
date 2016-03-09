'''
Neovim ui api is likely to change, also i do not understand really how and what it tries to do, it feels very granular and clunky. Makes it hard to do unit testing. Focuising on Integration testing...
'''

import sys
import time
import _thread as thread

#from neovim import attach
from neovim.ui.ui_bridge import UIBridge
from neovim.api import DecodeHook

from pytknvim.tk_ui import NvimTk
from pytknvim.util import attach_socket, attach_child
from pytknvim.test.util import compare_screens, send_tk_key

class MockNvimText(NvimTk):
    def thread_ui(self):
        nvim = attach_socket('/tmp/nv17')
        if sys.version_info[0] > 2:
            nvim = nvim.with_hook(DecodeHook())
        ui = self
        self._bridge = UIBridge()
        thread.start_new_thread(self._bridge.connect, (nvim, ui) )

        self.test_nvim = attach_socket('/tmp/nv17')
        time.sleep(0.5)

    def run_in_main(self):
        pass

class TestIntegration():


    def setup_class(cls):
        cls.nvimtk = MockNvimText()
        cls.nvimtk.thread_ui()

    def teardown_class(cls):
        cls.nvimtk.quit()
        time.sleep(0.5)
        

    def teardown_method(self, method):
        '''delete everything so we get a clean slate'''
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

