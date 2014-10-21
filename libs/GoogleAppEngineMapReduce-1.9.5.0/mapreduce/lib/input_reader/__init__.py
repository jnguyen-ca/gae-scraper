#!/usr/bin/env python
"""Various libraries regarding input readers and input in general."""
import sys
sys.path.append('libs/GoogleAppEngineMapReduce-1.9.5.0')

from mapreduce.lib.input_reader._gcs import GCSInputReader
from mapreduce.lib.input_reader._gcs import GCSRecordInputReader
from mapreduce.lib.input_reader._gcs import PathFilter

