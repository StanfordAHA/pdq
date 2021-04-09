from garnet.peak_core.peak_core import PeakCore
from lassen.sim import PE_fc



def PE():
    return PeakCore(PE_fc).circuit()
