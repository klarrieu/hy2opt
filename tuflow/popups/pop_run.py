try:
    from config import *
except:
    print("ImportERROR: Cannot find pool.")


class PopUpT(object):
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.iconbitmap(code_icon)

        # get run time
        tk.Label(self.top, text='').grid(sticky=tk.EW, row=0, column=0, columnspan=2, pady=yd)


        # define subfolder names for logging, check, and output