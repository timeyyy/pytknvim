
import tkinter as tk

from tk_ui import NvimTk

root = tk.Tk()

def ex1():
    tf = tk.Frame()
    tf.pack(side=tk.TOP)
    but = tk.Button(tf, text='i take focus')
    but.config(command=lambda: but.focus_set())
    but.pack()

    left = NvimTk(root)
    # Force Connection
    left.nvim_connect()
    left.pack(side=tk.LEFT)

    right = NvimTk(root)
    # Connection happens implicitly on packing or grdiing if required
    right.pack(side=tk.RIGHT, fill='both', expand=1)


def ex2():
    # Toplevel example
    text = NvimTk(root)
    text.nvim_connect('-u', 'NONE')
    text.pack(expand=1, fill='both')

# ex1()
ex2()
# root.protocol('WM_DELETE_WINDOW', NvimTk.kill_all)
root.mainloop()


