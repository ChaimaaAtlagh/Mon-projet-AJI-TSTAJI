"""Keep the stdlib tkinter modules discoverable in this Python installation."""


def pre_find_module_path(_hook_api):
    # Tcl/Tk is bundled explicitly by AJI_TSTAJI.spec below.
    pass
