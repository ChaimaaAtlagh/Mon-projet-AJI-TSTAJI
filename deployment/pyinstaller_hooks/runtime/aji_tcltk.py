"""Point the frozen GUI to its own packaged Tcl/Tk scripts."""

import os
import sys


os.environ["TCL_LIBRARY"] = os.path.join(sys._MEIPASS, "_tcl_data")
os.environ["TK_LIBRARY"] = os.path.join(sys._MEIPASS, "_tk_data")
