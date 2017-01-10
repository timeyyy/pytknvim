
import tkinter as tk

from tk_ui import NvimTk


root = tk.Tk()
# n = NvimTk()
# n.start()
left = NvimTk(root, toplevel=True) # Toplevel arg must be implemetned
left.pack(side=tk.LEFT)
# left.nvim_connect()
left.focus_set() # TODO onclick focus set?

# right = NvimTk(root, toplevel=True)
# right.pack(side=tk.RIGHT)
# right.nvim_connect()
# root.protocol('WM_DELETE_WINDOW', NvimTk.kill_all)
root.mainloop()
