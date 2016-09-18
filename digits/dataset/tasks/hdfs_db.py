# Copyright (c) 2015-2016, NVIDIA CORPORATION.  All rights reserved.
from __future__ import absolute_import

import os.path
import re
import sys

import digits
from digits.task import Task
from digits.utils import subclass, override

# NOTE: Increment this everytime the pickled object
PICKLE_VERSION = 1

@subclass
class HdfsDbTask(Task):
    """
    Reads information from a database
    """

    def __init__(self, database_hdfs_path, purpose,h5_file_field, **kwargs):
        """
        Arguments:
        database_hdfs_path -- path to the hdfs directory containing h5 files to analyze
        purpose -- what is this database going to be used for

        Keyword arguments:
        force_same_shape -- if True, enforce that every entry in the database has the same shape
        """
        self.force_same_shape = kwargs.pop('force_same_shape', False)

        super(HdfsDbTask, self).__init__(**kwargs)
        self.pickver_task_analyzedb = PICKLE_VERSION

        self.hdf5locations = os.path.join(kwargs.pop('job_dir'),purpose.replace(' ','_')+'.txt')
        self.database= database_hdfs_path #
        self.purpose = purpose
        self.backend = 'hdf5'

        h5_fields = h5_file_field.split(',')
        fields = []
        for f in h5_fields:
            fields.append(f.strip())
        self.h5_file_fields = fields

        # Results
        self.h5_file_count = None

        #
        self.data_dimensions = {}

        self.image_count = None
        self.image_width = None
        self.image_height = None
        self.image_channels = None


        self.analyze_db_log_file = 'analyze_db_%s.log' % '-'.join(p.lower() for p in self.purpose.split())

    def __getstate__(self):
        state = super(HdfsDbTask, self).__getstate__()
        if 'analyze_db_log' in state:
            del state['analyze_db_log']
        return state

    def __setstate__(self, state):
        super(HdfsDbTask, self).__setstate__(state)
        if not hasattr(self, 'backend') or self.backend is None:
            self.backend = 'hdf5'

    @override
    def name(self):
        return 'HDFS DB (%s)' % (self.purpose)

    @override
    def html_id(self):
        return 'task-analyze-db-%s' % '-'.join(p.lower() for p in self.purpose.split())

    @override
    def offer_resources(self, resources):
        key = 'analyze_db_task_pool'
        if key not in resources:
            return None
        for resource in resources[key]:
            if resource.remaining() >= 1:
                return {key: [(resource.identifier, 1)]}
        return None

    @override
    def task_arguments(self, resources, env):
        args = [sys.executable, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(digits.__file__))),
            'tools', 'hdfs_db.py'),
                self.hdf5locations,
                self.database,
                ",".join(self.h5_file_fields),
                ]
        if self.force_same_shape:
            args.append('--force-same-shape')
        else:
            args.append('--only-count')

        return args

    @override
    def before_run(self):
        super(HdfsDbTask, self).before_run()
        self.analyze_db_log = open(self.path(self.analyze_db_log_file), 'a')

    @override
    def process_output(self, line):
        self.analyze_db_log.write('%s\n' % line)
        self.analyze_db_log.flush()

        timestamp, level, message = self.preprocess_output_digits(line)
        if not message:
            return False

        # progress
        match = re.match(r'Progress: (\d+)\/(\d+)', message)
        if match:
            self.progress = float(match.group(1))/float(match.group(2))
            self.emit_progress_update()
            return True

        # total count
        match = re.match(r'Total h5 entries: (\d+)', message)
        if match:
            self.h5_file_count = int(match.group(1))
            return True

        match = re.match(r'key (\d+) shape (\d+)x(\d+)x(\d+)', message)
        if match:
            j = int(match.group(1))
            key = self.h5_file_fields[j]
            width = int(match.group(2))
            height = int(match.group(3))
            channels = int(match.group(4))
            self.data_dimensions[key] = [width,height,channels]
            if key == 'data':
                self.image_width = width
                self.image_height = height
                self.image_channels = channels
            self.logger.debug('%s seen' % key)
            return True

        # image dimensions
        match = re.match(r'(\d+) data_entries', message)
        if match:
            self.image_count = int(match.group(1))
            self.logger.debug('Images nbs %s' % self.image_count)
            return True

        if level == 'warning':
            self.logger.warning('%s: %s' % (self.name(), message))
            return True
        if level in ['error', 'critical']:
            self.logger.error('%s: %s' % (self.name(), message))
            self.exception = message
            return True

        return True

    @override
    def after_run(self):
        super(HdfsDbTask, self).after_run()
        self.analyze_db_log.close()

    def image_type(self):
        """
        Returns an easy-to-read version of self.image_channels
        """
        if self.image_channels is None:
            return None
        elif self.image_channels == 1:
            return 'GRAYSCALE'
        elif self.image_channels == 3:
            return 'COLOR'
        else:
            return '%s-channel' % self.image_channels

    def get_h5_file_fields(self):
        return self.h5_file_fields
