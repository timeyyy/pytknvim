'''
some of these should go into neovim python client
'''
from __future__ import print_function

import os
import time
from subprocess import *
from threading import Thread
import shlex
import string
import random
from functools import wraps
from distutils.spawn import find_executable

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


def attach_child(nvim_args, exec_name='nvim'):
    nvim_binary = find_executable(exec_name)
    args = [nvim_binary, '--embed']
    if nvim_args:
        args.extend(nvim_args)
    return attach('child', argv=args)


def attach_headless(nvim_args=None, path=None):
    if not path:
        path = '/tmp/nvim' + rand_str(8)
    os.environ['NVIM_LISTEN_ADDRESS'] = path
    dnull = open(os.devnull)
    # TODO WHY USE SHLEX???
    cmd = shlex.split('nvim --headless')
    if nvim_args:
        cmd.extend(nvim_args)
    proc = Popen(cmd,
            stdin=dnull,
            stdout=dnull,
            stderr=dnull)
    dnull.close()
    while proc.poll() or proc.returncode is None:
        try:
            print('connected to headless socket', path)
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
    if state == 'Shift':
        send.append('S')
    elif state == 'Ctrl':
        send.append('C')
    elif state =='Alt':
        send.append('A')
    send.append(key)
    return '<' + '-'.join(send) + '>'


def _split_color(n):
    return ((n >> 16) & 0xff, (n >> 8) & 0xff, n & 0xff,)


def _invert_color(r, g, b):
    return (255 - r, 255 - g, 255 - b,)


def _stringify_color(r, g, b):
    return '#{0:0{1}x}'.format((r << 16) + (g << 8) + b, 6)


def debug_echo(func):
    '''used on method to simply print the function name and
    parameters if self.debug_echo = True,
    the function will not execute'''
    @wraps(func)
    def deco(*args, **kwargs):
        try:
            debug = args[0].debug_echo
        except AttributeError:
            debug = False
        if debug:
            if len(args) == 1:
                to_print = []
            else:
                to_print = args[1:]
            print(func.__name__, repr(to_print), **kwargs)

        return func(*args, **kwargs)
    return deco


def rate_limited(max_per_second, mode='wait', delay_first_call=False):
    """
    Decorator that make functions not be called faster than

    set mode to 'kill' to just ignore requests that are faster than the
    rate.

    set mode to 'refresh_timer' to reset the timer on successive calls

    set delay_first_call to True to delay the first call as well
    """
    lock = threading.Lock()
    min_interval = 1.0 / float(max_per_second)
    def decorate(func):
        last_time_called = [0.0]
        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            def run_func():
                lock.release()
                ret = func(*args, **kwargs)
                last_time_called[0] = time.perf_counter()
                return ret
            lock.acquire()
            elapsed = time.perf_counter() - last_time_called[0]
            left_to_wait = min_interval - elapsed
            if delay_first_call:
                if left_to_wait > 0:
                    if mode == 'wait':
                        time.sleep(left_to_wait)
                        return run_func()
                    elif mode == 'kill':
                        lock.release()
                        return
                else:
                    return run_func()
            else:
                if not last_time_called[0] or elapsed > min_interval:
                    return run_func()
                elif mode == 'refresh_timer':
                    print('Ref timer')
                    lock.release()
                    last_time_called[0] += time.perf_counter()
                    return
                elif left_to_wait > 0:
                    if mode == 'wait':
                        time.sleep(left_to_wait)
                        return run_func()
                    elif mode == 'kill':
                        lock.release()
                        return
        return rate_limited_function
    return decorate

