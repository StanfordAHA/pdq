from lassen.sim import PE_fc
from garnet.peak_core.peak_core import PeakCore

def PE():
    return PeakCore(PE_fc).circuit()
    
