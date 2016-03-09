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
        nvim = attach_socket('/tmp/nv7')
        if sys.version_info[0] > 2:
            nvim = nvim.with_hook(DecodeHook())
        ui = self
        self._bridge = UIBridge()
        thread.start_new_thread(self._bridge.connect, (nvim, ui) )

        self.test_nvim = attach_socket('/tmp/nv7')
        time.sleep(1)

    def run_in_main(self):
        pass

class TestIntegration():
        
    def setup_class(cls):
        cls.nvimtk = MockNvimText()
        cls.nvimtk.thread_ui()

    def teardown_class(cls):
        '''just for sanity check'''
        compare_screens(TestIntegration.nvimtk)

    def teardown_method(self, method):
        '''delete everything so we get a clean slate'''
        tknvim = TestIntegration.nvimtk
        buf = tknvim.test_nvim.buffers[0]
        buf[:] = [""]

    def test_load(self):
        compare_screens(TestIntegration.nvimtk)

    def test_basic_insert(self):
        #nvimtk = MockNvimText()
        #nvimtk.thread_ui()
        pass
        compare_screens(TestIntegration.nvimtk)

