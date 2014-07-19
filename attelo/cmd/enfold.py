"split data into folds"

from __future__ import print_function
import argparse
import json
import random
import sys

from ..args import\
    add_common_args_lite,\
    args_to_features
from ..fold import make_n_fold
from ..io import read_data


NAME = 'enfold'


def _prepare_folds(features, num_folds, table, shuffle=True):
    """Return an N-fold validation setup respecting a property where
    examples in the same grouping stay in the same fold.
    """
    if shuffle:
        random.seed()
    else:
        random.seed("just an illusion")

    return make_n_fold(table,
                       folds=num_folds,
                       meta_index=features.grouping)


def config_argparser(psr):
    "add subcommand arguments to subparser"

    add_common_args_lite(psr)
    psr.set_defaults(func=main)
    psr.add_argument("--nfold", "-n",
                     default=10, type=int,
                     help="nfold cross-validation number (default 10)")
    psr.add_argument("-s", "--shuffle",
                     default=False, action="store_true",
                     help="if set, ensure a different cross-validation "
                     "of files is done, otherwise, the same file "
                     "splitting is done everytime")
    psr.add_argument("--output", type=argparse.FileType('w'),
                     help="save folds to a json file")


def main(args):
    "subcommand main (called from mother script)"

    features = args_to_features(args)
    data_attach, _ = read_data(args.data_attach, None, verbose=True)

    fold_struct = _prepare_folds(features,
                                 args.nfold,
                                 data_attach,
                                 shuffle=args.shuffle)

    json_output = args.output or sys.stdout
    json.dump(fold_struct, json_output, indent=2)
    if not args.output:
        print("")
