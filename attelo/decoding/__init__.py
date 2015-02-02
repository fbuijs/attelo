'''
Decoding in attelo consists in building discourse graphs from a
set of attachment/labelling predictions.

There are two kinds of modules in this package:

    * decoders: eg., baseline, greedy, mst: convert probability distributions
      into graphs

    * management: by rights the important bits of these should have been
      re-exported here so you'd never need to look into attelo.decoding.control
      or attelo.decoding.util unless you were writing a decoder yourself
'''

# pylint: disable=too-few-public-methods

from __future__ import print_function
from collections import namedtuple

# pylint: disable=wildcard-import
# (just for re-export)
from .control import *
from .util import DecoderException

from .astar import (AstarDecoder)
from .baseline import LastBaseline, LocalBaseline
from .mst import MstDecoder
from .greedy import LocallyGreedy


class DecoderArgs(namedtuple("DecoderAgs",
                             ["threshold",
                              "astar",
                              "use_prob"])):
    """
    Superset of parameters needed by attelo decoders. Attelo decoders
    accept a wide variety of arguments, sometimes overlapping, often
    not. At the end of the day all these parameters find their way into
    data structure (sometimes hived off into sections like `astar`).
    We also provide below universal wrappers that pick out just the
    parameters needed by the individual decoders

    :param use_prob: `True` if model scores are probabilities in [0,1]
                     (to be mapped to -log), `False` if arbitrary scores
                     (to be untouched)
    :type use_prob: bool

    :param threshold: For some decoders, a probability floor that helps
                      the decoder decide whether or not to attach something
    :type threshold: float or None

    :param astar: Config options specific to the A* decoder
    :type astar: AstarArgs
    """
    def __new__(cls,
                threshold=None,
                astar=None,
                use_prob=True):
        sup = super(DecoderArgs, cls)
        return sup.__new__(cls,
                           threshold=threshold,
                           astar=astar,
                           use_prob=use_prob)


def _mk_local_decoder(config, default=0.5):
    """
    Instantiate the local decoder
    """
    if config.threshold is None:
        threshold = default
        print("using default threshold of {}".format(threshold),
              file=sys.stderr)
    else:
        threshold = config.threshold
        print("using requested threshold of {}".format(threshold),
              file=sys.stderr)
    return LocalBaseline(threshold, config.use_prob)


DECODERS = {"last": lambda _: LastBaseline(),
            "local": _mk_local_decoder,
            "locallyGreedy": lambda _: LocallyGreedy(),
            "mst": lambda c: MstDecoder(c.use_prob),
            "astar": lambda c: AstarDecoder(c.astar)}
"""
Dictionary (`string -> DecoderAgs -> Decoder`) of decoder names (recognised by
the command line interface) to wrappers. Wrappers smooth out the differences
between decoders, making it so that each known decoder accepts the universal
:py:class:DecoderArgs:
"""
