'''
these should go into neovim python client
'''
import os
import subprocess as sub
from threading import Thread

from neovim import attach

def attach_socket(path=None):
    '''does it auto'''
    def open_nvim():
        proc = sub.Popen('NVIM_LISTEN_ADDRESS=/tmp/nvim nvim', stdin=sub.PIPE, stdout=sub.PIPE, shell=True)
        proc.communicate()

    # THIS IS DOESNT WORK UNRELIBALE 
    #path = os.environ.get('NVIM_LISTEN_ADDRESS')
    if not path:
        print('threading')
        t = Thread(target=open_nvim)
        t.start()
        return attach('socket', path='/tmp/nvim')
    else:
        print('attaching socket')
        return attach('socket', path=path)


def attach_child():
    return attach('child', argv=['nvim', '--embed'])

