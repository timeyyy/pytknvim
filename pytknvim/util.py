'''
some of these should go into neovim python client
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

def attach_headless(*nvim_args, path=None):
    if not path:
        path = '/tmp/nvim' + rand_str(8)
    os.environ['NVIM_LISTEN_ADDRESS'] = path
    dnull = open(os.devnull)
    # TODO WHY USE SHLEX???
    cmd = shlex.split('nvim --headless')
    cmd.extend(nvim_args)
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


def _stringify_key(key, state):
    send = []
    if state:
        if 'Shift' in key:
            send.append('S')
        elif 'Ctrl' in key:
            send.append('C')
        elif 'Alt' in key:
            send.append('A')
    send.append(key)
    return '<' + '-'.join(send) + '>'


def _split_color(n):
    return ((n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff,)


def _invert_color(r, g, b):
    return (255 - r, 255 - g, 255 - b,)


def _stringify_color(r, g, b):
    return '#{0:0{1}x}'.format((r << 16) + (g << 8) + b, 6)
