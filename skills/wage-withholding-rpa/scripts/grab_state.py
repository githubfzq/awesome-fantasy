# -*- coding: utf-8 -*-
from PIL import ImageGrab
import ctypes
user32 = ctypes.windll.user32
user32.SetProcessDPIAware()
ImageGrab.grab().save(r"\Mac\Home\Documents\rpa\state_now.png")
