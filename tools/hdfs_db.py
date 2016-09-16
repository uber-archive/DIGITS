#!/usr/bin/env python2
# Copyright (c) 2015-2016, NVIDIA CORPORATION.  All rights reserved.

import argparse
import glob
import logging
import os
import random
import sys
import time
import threading

import h5py

# Find the best implementation available
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Add path for DIGITS package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import digits.config
digits.config.load_config()
from digits import log

# Run load_config() first to set path to Caffe

logger = logging.getLogger('digits.tools.hdfs_db')



CONFIGFILE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGFILE=os.path.join(CONFIGFILE,'opuspro_hdfs')
EXPORT='export PATH=/usr/local/hadoop/bin:/usr/local/hadoop/sbin:$PATH && export JAVA_HOME=/usr '
HDFSGET=EXPORT+' && hdfs --config '+ CONFIGFILE +' dfs -get '
HDFSLS=EXPORT+' && hdfs --config '+ CONFIGFILE +' dfs -ls '

def download_hdfs_directory(h5directory, dest_dir, ext = ['*.h5']):
    #for e in ext:
    e = '*.h5'
    os.system(HDFSGET+ os.path.join(h5directory,e) + ' '+ os.path.join(dest_dir,'.'))
    logger.info( 'cmd : %s' % 'hdfs dfs -get '+ os.path.join(h5directory,e) + ' '+ os.path.join(dest_dir,'.'))


semaphore = threading.Semaphore(4)
def download_h5_file(f , dirh5):
    with semaphore:
        cmd = HDFSGET+ f + ' ' + dirh5
        os.system(cmd)



def download_and_analyze_db(h5textfile, h5directory,
            h5key,
            only_count=False,
            force_same_shape=False):
    """
    Looks into hdf5 directory and download the files
    Args:
        h5directory:
        database:
        h5key:
        only_count:
        force_same_shape:

    Returns:

    """
    start_time = time.time()
    update_time = None

    dirname = os.path.dirname(h5textfile)
    bname = os.path.basename(h5textfile)
    bname = os.path.splitext(bname)[0]
    dirh5 = os.path.join(dirname,bname+'_H5')
    if not os.path.exists(dirh5):
        os.mkdir(dirh5)

    logger.info('hdfs directory containing h5 files: '+ h5directory)

    # collect download information
    ext='*.h5'
    list_of_h5file = os.path.join(dirh5, bname+'_list_from_hdfs.txt')
    cmd = HDFSLS+ os.path.join(h5directory,ext) + " | awk '{print $8}' > "+ list_of_h5file
    logger.info(cmd)
    os.system(cmd)
    logger.info('listof hdfs h5 file placed at : '+ list_of_h5file)

    h5files_list = []
    with open(list_of_h5file,'r') as src:
        for x in src:
            x = x.rstrip()
            h5files_list.append(x)

    # start the download
    threads=[]
    explore_r = min(16,len(h5files_list))
    for j in range(16):
        #cmd = 'export PATH=/usr/local/hadoop/bin:/usr/local/hadoop/sbin:$PATH && hdfs dfs -get '+ f + ' ' + dirh5
        #os.system(cmd)
        f = h5files_list[j]
        t = threading.Thread(target=download_h5_file, args=(f,dirh5))
        threads.append(t)
        t.start()

    # check all threads are terminated
    all_threads_alive = True
    while all_threads_alive:
        loccount=0
        all_threads_alive=False
        for t in threads:
            if t.isAlive():
                all_threads_alive=True
            else:
                loccount+=1
        time.sleep(2)
        logger.debug('Progress: %s/%s' % (loccount, len(threads)))

    for t in threads:
        t.join()




    # run the database analysis
    analyze_db(dirh5,
                h5textfile,
                h5key,
                h5files_list,
                only_count=False,
                force_same_shape=False)


    return True


def analyze_db(h5directory,
            database,
            h5key,
            h5files_list,
            only_count=False,
            force_same_shape=False
        ):
    """
    Looks at the data in a prebuilt database and verifies it
        Also prints out some information about it
    Returns True if all entries are valid

    Arguments:
    database -- path to the database

    Keyword arguments:
    only_count -- only count the entries, don't inspect them
    force_same_shape -- throw an error if not all images have the same shape
    """
    start_time = time.time()
    update_time = None
    logger.info('h5 directory containing h5 files: '+ h5directory)
    logger.info('name of the database file: ' + database)

    #retrieve the h5 files and shuffle
    #
    random.shuffle(h5files_list)
    with open(database,'w') as dst:
        for h5 in h5files_list:
            dst.write(h5 + '\n')

    #count the number of h5 files
    count = len(h5files_list)
    logger.info('Total h5 entries: %d' % count)
    if count == 0:
        return True

    # determine the size of the first key
    h5files = glob.glob(os.path.join(h5directory,'*h5'))
    h5keys = h5key.split(",")
    f = h5py.File(h5files[0])
    shapes=[]
    for j,key in enumerate(h5keys):
        try:
            data = f[key]
        except:
            logger.error('the key %s does not exist in the h5 file ' % h5keys[0])
        s = data[0].shape
        if len(s)==1:
            s = (1,1)+s
        elif len(s)==2:
            s = (1,)+s
        elif len(s)==0:
            s = (1,1,1)

        shape = '%sx%sx%s' % (s[2], s[1], s[0])
        shapes.append(shape)
        logger.info('key %s shape %s' % (j, shape))
    f.close()

    #count the number of individual
    count = 0
    for j, h5 in enumerate(h5files):
        f = h5py.File(h5)
        d = f[h5keys[-1]]
        count+= len(d)
        f.close()
        if update_time is None or (time.time() - update_time) > 2:
            logger.debug('Progress: %s/%s' % (j, len(h5files)))
            update_time = time.time()
        os.remove(h5)


    #display some metrics
    estimated_count = float(count)/len(h5files)*len(h5files_list)
    logger.info('%d data_entries' % int(estimated_count))
    return True

def main(h5directory,
            database,
            h5key,
            only_count=False,
            force_same_shape=False):

    start_time = time.time()
    #if os.path.exists(h5directory):
    #    logger.info('file system detected')
    #    endbool = analyze_db(h5directory,database,h5key,only_count,force_same_shape)
    #else:
    logger.info('hdfs detected')
    endbool = download_and_analyze_db(h5directory,database,h5key,only_count,force_same_shape)

    logger.info('Completed in %s seconds.' % (time.time() - start_time,))
    return endbool

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HDFS-Db tool - DIGITS')

    ### Positional arguments

    parser.add_argument('h5files',
            help='Path to the h5file directory in hdfs')

    parser.add_argument('database',
            help='Path to the database directory')

    parser.add_argument('h5key',
            help='h5key in the h5 files')

    ### Optional arguments

    parser.add_argument('--only-count',
            action="store_true",
            help="Only print the number of entries, don't analyze the data")

    parser.add_argument('--force-same-shape',
            action="store_true",
            help='Throw an error if not all entries have the same shape')

    args = vars(parser.parse_args())

    if main(args['h5files'],
                  args['database'],
                  args['h5key'],
            only_count = args['only_count'],
            force_same_shape = args['force_same_shape'],
            ):
        sys.exit(0)
    else:
        sys.exit(1)

