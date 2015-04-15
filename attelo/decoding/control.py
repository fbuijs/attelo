"""
Central interface to the decoders
"""

from __future__ import print_function
from enum import Enum

import numpy as np

from attelo.table import (for_attachment, for_labelling, for_intra,
                          UNKNOWN)
from .interface import (LinkPack)
from .intra import (IntraInterPair, partition_subgroupings)
from .util import (DecoderException)
# pylint: disable=too-few-public-methods


class DecodingMode(Enum):
    '''
    How to do decoding:

        * joint: predict attachment/relations together
        * post_label: predict attachment, then independently
                      predict relations on resulting graph
    '''
    joint = 1
    post_label = 2

# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _add_labels(dpack, models, predictions):
    """given a list of predictions, predict labels for a given set of edges
    (=post-labelling an unlabelled decoding)

    :param pack: data pack

    :type predictions: [prediction] (see `attelo.decoding.interface`)
    :rtype: [prediction]
    """

    relate_pack = for_labelling(dpack)
    labels, scores_l = models.relate.transform(relate_pack)
    # pylint: disable=no-member
    lbls = np.argmax(scores_l, axis=1)
    # pylint: enable=no-member
    label_dict = {(edu1.id, edu2.id): labels[lbl]
                  for (edu1, edu2), lbl in
                  zip(dpack.pairings, lbls)}

    def update(link):
        '''replace the link label (the original by rights is something
        like "unlabelled"'''
        edu1, edu2, old_label = link
        can_replace = old_label == UNKNOWN
        label = label_dict[(edu1, edu2)] if can_replace else old_label
        return (edu1, edu2, label)

    res = []
    for pred in predictions:
        res.append(update(p) for p in pred)
    return res


def build_lpack(dpack, models, mode):
    """
    Extract candidate links (scores and proposed labels
    for each edu pair) from the models for all instances
    in the datapack

    :type models: Team(model)

    :rtype: LinkPack
    """
    if mode == DecodingMode.joint:
        if not models.attach.can_predict_proba:
            oops = ('Attachment model does not know how to predict '
                    'probabilities. It should only be used in post '
                    'labelling mode')
            raise DecoderException(oops)
        if not models.relate.can_predict_proba:
            raise DecoderException('Relation labelling model does not '
                                   'know how to predict probabilities')

        attach_pack = for_attachment(dpack)
        relate_pack = for_labelling(dpack)
        scores_ad = models.attach.transform(attach_pack)
        labels, scores_l = models.relate.transform(relate_pack)
        return LinkPack(edus=dpack.edus,
                        pairings=dpack.pairings,
                        labels=labels,
                        scores_ad=scores_ad,
                        scores_l=scores_l)
    elif mode == DecodingMode.post_label:
        attach_pack = for_attachment(dpack)
        scores_ad = models.attach.transform(attach_pack)
        # pylint: disable=no-member
        scores_l = np.ones((len(dpack), 1))
        # pylint: enable=no-member
        return LinkPack.unlabelled(edus=dpack.edus,
                                   pairings=dpack.pairings,
                                   scores_ad=scores_ad)
    else:
        raise ValueError('Unknown labelling mode: ' + mode)


def _maybe_post_label(dpack, models, predictions, mode):
    """
    If post labelling mode is enabled, apply the best label from
    our relation model to all links in the prediction
    """
    if mode == DecodingMode.post_label:
        return _add_labels(dpack, models, predictions)
    else:
        return predictions


def decode(dpack, models, decoder, mode):
    """
    Decode every instance in the attachment table (predicting
    relations too if we have the data/model for it).

    Use intra/inter-sentential decoding if the decoder is a
    :py:class:`IntraInterDecoder` (duck typed). Note that
    you must also supply intra/inter sentential models
    for this

    Return the predictions made.

    :type: models: Team(model) or IntraInterPair(Team(model))
    """
    if callable(getattr(decoder, "decode_sentence", None)):
        func = decode_intra_inter
    else:
        func = decode_vanilla
    return func(dpack, models, decoder, mode)


def decode_vanilla(dpack, models, decoder, mode):
    """
    Decode every instance in the attachment table (predicting
    relations too if we have the data/model for it).
    Return the predictions made

    :type models: Team(model)
    """
    lpack = build_lpack(dpack, models, mode)
    predictions = decoder.decode(lpack)
    return _maybe_post_label(dpack, models, predictions, mode)


def decode_intra_inter(dpack, models, decoder, mode):
    """
    Variant of `decode` which uses an IntraInterDecoder rather than
    a normal decoder

    :type models: IntraInterPair(Team(model))
    """
    # intrasentential target links are slightly different
    # in the fakeroot case (this only really matters if we
    # are using an oracle)
    dpacks = IntraInterPair(intra=for_intra(dpack),
                            inter=dpack)
    lpacks =\
        IntraInterPair(intra=build_lpack(dpacks.intra,
                                         models.intra,
                                         mode),
                       inter=build_lpack(dpacks.inter,
                                         models.inter,
                                         mode))

    # launch a decoder per sentence
    sent_parses = []
    for mini_lpack in partition_subgroupings(lpacks.intra):
        sent_predictions = decoder.decode_sentence(mini_lpack)
        sent_parses.append(_maybe_post_label(dpacks.intra, models.intra,
                                             sent_predictions, mode))
    ##########

    doc_predictions = decoder.decode_document(lpacks.inter, sent_parses)
    return _maybe_post_label(dpacks.inter, models.inter,
                             doc_predictions, mode)
