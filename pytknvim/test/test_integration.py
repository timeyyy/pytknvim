'''
Neovim ui api is likely to change, also i do not understand really how and what it tries to do, it feels very granular and clunky. Makes it hard to do unit testing. Focuising on Integration testing...
'''

import sys
import time
import _thread as thread
from subprocess import Popen, PIPE

from neovim.ui.ui_bridge import UIBridge
from neovim.api import DecodeHook

from pytknvim.tk_ui import NvimTk
from pytknvim.util import attach_socket, attach_child
from pytknvim.test.util import compare_screens, send_tk_key
from pytknvim.test.util import rand_str

class MockNvimText(NvimTk):


    def spawn_nvim(self):
        '''Loads up neovim on a radom address'''
        #Connecting to multiple embeded instances didn't work
        named_pipe = '/tmp/nvim{0}'.format(rand_str(4))
        cmd = 'NVIM_LISTEN_ADDRESS={0} nvim'.format(named_pipe)
        def nvim(cmd):
            # This worked a bit
            proc = Popen(cmd,
                    shell=True,
                    stdin=PIPE)
                    #stdout=PIPE,
                    #stderr=PIPE)
            # THESE DIDND TWORK
                #proc = Popen(cmd, stdout=PIPE, stdin=PIPE)
                #proc = Popen(cmd)
                #proc = Popen(cmd, shell=True)
            proc.communicate()
        thread.start_new_thread(nvim, (cmd,))
        time.sleep(1)
        return named_pipe


    def thread_ui(self):
        '''starts our us threaded so we can run tests'''
        named_pipe = self.spawn_nvim()
        nvim = attach_socket(named_pipe)
        if sys.version_info[0] > 2:
            nvim = nvim.with_hook(DecodeHook())
        ui = self
        self._bridge = UIBridge()
        thread.start_new_thread(self._bridge.connect, (nvim, ui) )

        self.test_nvim = attach_socket(named_pipe)
        time.sleep(1)

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

