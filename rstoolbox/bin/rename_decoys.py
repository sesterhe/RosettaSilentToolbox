#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. codeauthor:: Jaume Bonet <jaume.bonet@gmail.com>

.. affiliation::
    Laboratory of Protein Design and Immunoengineering <lpdi.epfl.ch>
    Bruno Correia <bruno.correia@epfl.ch>
"""
# Standard Libraries
import argparse
import gzip
import os

# External Libraries

# This Library
from rstoolbox.io import parse_rosetta_file


def get_options(*args, **kwds):

    parser = argparse.ArgumentParser(
        description="Rename the decoys with a new rule in the silent file ")

    parser.add_argument('-in:file', dest='ifile', action='store',
                        help='Input silent file', default=None )
    parser.add_argument('-prefix', dest='prefix', action='store',
                        help='Prefix for the new naming schema', default=None )
    parser.add_argument('-out:file', dest='ofile', action='store',
                        help='Output silent file', default=None )
    parser.add_argument('-overwrite', dest='force', action='store_true',
                        help='Allow overwrite', default=False)

    options = parser.parse_args()

    if options.ifile is None:
        raise AttributeError("A filename has to be provided.")
    if options.ofile is None:
        raise AttributeError("Output filename must be provided")
    if options.prefix is None:
        raise AttributeError("A prefix for the naming schema needs to be provided")
    if os.path.isfile( options.ofile ) and not options.force:
        raise IOError("File {0} exists and will not be overwritten.".format( options.ofile ) )
    return options


def new_names( count, prefix ):
    return "{0}_{1:05d}".format(prefix, count)


def main( options ):
    # Get names and make new ones
    names = parse_rosetta_file( options.ifile, {"scores": ["description"]} )
    names["count"] = names.index + 1
    names["new"]   = names.apply( lambda row: new_names(row["count"], options.prefix), axis=1 )

    # Load the silentfile and change names
    fd   = gzip.open( options.ifile ) if options.ifile.endswith(".gz") else open( options.ifile )
    data = "".join(fd.readlines())
    fd.close()

    for index, row in names.iterrows():
        data = data.replace(row["description"], row["new"])

    # Save and write
    is_gz = options.ofile.endswith(".gz")
    fd = gzip.open( options.ofile, "w" ) if is_gz else open( options.ofile, "w" )
    fd.write(data.encode('utf-8') if is_gz else data)
    fd.close()


if __name__ == '__main__':
    main( get_options() )
