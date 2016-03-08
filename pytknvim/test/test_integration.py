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
        nvim = attach_socket('/tmp/nv6')
        if sys.version_info[0] > 2:
            nvim = nvim.with_hook(DecodeHook())
        ui = self
        self._bridge = UIBridge()
        thread.start_new_thread(self._bridge.connect, (nvim, ui) )
        #self.root.after_idle(1, run_in_main)

        # seems we have to get another connection which i'm not wure how to do when embedded
        self.test_nvim = attach_socket('/tmp/nv6')
        time.sleep(2)

    def run_in_main(self):
        pass

class TestIntegration():
        
    def test_load(self):
        nvimtk = MockNvimText()
        nvimtk.thread_ui()
        compare_screens(nvimtk)

