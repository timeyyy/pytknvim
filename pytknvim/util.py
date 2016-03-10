'''
these should go into neovim python client
'''
import os
import time
from subprocess import *
from threading import Thread
import shlex
import string
import random

from neovim import attach

def attach_socket(path=None):
    '''does it auto'''
    def open_nvim():
        proc = Popen('NVIM_LISTEN_ADDRESS=/tmp/nvim nvim',
                    stdin=PIPE, stdout=PIPE, shell=True)
        proc.communicate()

    # THIS IS DOESNT WORK UNRELIBALE 
    #path = os.environ.get('NVIM_LISTEN_ADDRESS')
    if not path:
        print('threading')
        t = Thread(target=open_nvim)
        t.start()
        #todo make this give a random path
        return attach('socket', path='/tmp/nvim')
    else:
        print('attaching socket')
        return attach('socket', path=path)


def attach_child():
    return attach('child', argv=['nvim', '--embed'])

def attach_headless(path=None):
    if not path:
        path = '/tmp/nvim' + rand_str(8)
    os.environ['NVIM_LISTEN_ADDRESS'] = path
    dnull = open(os.devnull)
    cmd = shlex.split('nvim --headless')
    proc = Popen(cmd,
            stdin=dnull,
            stdout=dnull,
            stderr=dnull)
    dnull.close()
    while proc.poll() or proc.returncode is None:
        try:
            nvim = attach('socket', path=path)
            break
        except IOError:
            # Socket not yet ready
            time.sleep(0.05)

    return nvim


def rand_str(length):
    '''returns a random string of length'''
    chars = []
    for i in range(length):
        chars.append(random.choice(string.ascii_letters))
    return ''.join(char for char in chars)
