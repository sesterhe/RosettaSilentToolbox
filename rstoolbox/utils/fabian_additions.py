"""
.. func:: get_wanted_aa
"""

# Standard Libraries
import re

# External Libraries
import pandas as pd
import numpy as np
from six.moves import reduce

# This Library

__all__ = ['get_wanted_aa']

def get_wanted_aa(dat,indices): 
    b = {}
    for ind,row in dat["sequence_A"].iteritems():
        newseq = []
        for f in indices:
            newseq.append(row[f-1])
            b.update({ind:''.join(newseq)})
    dat["coreseq"] = pd.DataFrame.from_dict(b,orient="index")
    return dat
