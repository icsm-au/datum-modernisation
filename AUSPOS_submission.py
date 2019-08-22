# ----------------------------------------------------------------------
# AUSPOS_submission.py
# ----------------------------------------------------------------------
# Author:   Nic Gowans
# Date:     22AUG2019
# Purpose:  To read a list of RINEX files and metadata, and one-by-one
#           submit to the AUSPOS online GPS processing service
# ----------------------------------------------------------------------
# Usage:    CMD:\>python AUSPOS_submission.py <Rinex_metadata_files.csv>
# ----------------------------------------------------------------------
# Notes:    Before running, the user must update:
#               - the directory where the RINEX files are stored
#               - their preferred email address
# ----------------------------------------------------------------------


import os
import requests
import re
import time
import timeit
import datetime

start = timeit.default_timer()

# ----------------------------------------------------------------------
# set script input files, targets and directories
# ----------------------------------------------------------------------

# input data file
rnx_list = os.sys.argv[1]

# AUSPOS website
post_target = 'http://www.ga.gov.au/bin/gps.pl'

# User input
rnx_dir = r''
email_add = ''

# ----------------------------------------------------------------------
# read RINEX metadata .csv file
# ----------------------------------------------------------------------

print()
print(' Consuming input file: {:s}'.format(rnx_list))

meta_dict = {}

csv_fh = open(rnx_list,'r')

# write session metadata to dictionary
for line in csv_fh:
    items = line.split(',')
    if len(items) > 2:
        rnx_file = items[0]
        HI = items[1]
        ant = items[2].strip()

        meta_dict[rnx_file] = {
            'HI': HI,
            'ant': ant
        }

csv_fh.close()


# ----------------------------------------------------------------------
# submit data to AUSPOS, one-by-one
# ----------------------------------------------------------------------
print()
print(' Submitting data to AUSPOS:')

submitted_count = 0

total_rnx = int(len(meta_dict))

rnx_count = 0

for rnx in meta_dict:
    rnx_count += 1

    # update screen
    print('   Submitting session {:d}/{:d} - {:s}'.format(rnx_count, total_rnx, rnx))

    # set path to rinex file
    rnx_path = os.path.join(rnx_dir, rnx)

    form_file = {
        'upload1': open(rnx_path)
    }

    # set metadata for rinex session
    form_data = {
        'num_files': '1',
        'submit_files': 'upload',
        'height1': meta_dict[rnx]['HI'],
        'type1': meta_dict[rnx]['ant'],
        'email': email_add,
        'submit': 'submit'
    }

    # log AUSPOS response
    response = requests.post(post_target, files=form_file, data=form_data)

    AUSPOS_message = str(response.content)

    # find referenceID with regex
    referenceID_list = re.findall('[#][0-9]+[\.]', AUSPOS_message)
    referenceID = referenceID_list[0][1:-1]

    meta_dict[rnx]['job_ref'] = referenceID

    submitted_count += 1

    #  wait a few seconds as not to overwhelm AUSPOS
    time.sleep(5)


# ----------------------------------------------------------------------
# write reference ID to file
# ----------------------------------------------------------------------

results_file = rnx_list[:-4] + '_results.csv'

results_fh = open(results_file, 'w')

outStr = ''

for rnx in meta_dict:

    HI = meta_dict[rnx]['HI']
    ant = meta_dict[rnx]['ant']
    job_ref = meta_dict[rnx]['job_ref']

    outStr += '{:s},{:s},{:s},{:s}\n'.format(rnx, HI, ant, job_ref)

results_fh.write(outStr)

results_fh.close()


# ----------------------------------------------------------------------
# print summary
# ----------------------------------------------------------------------

stop = timeit.default_timer()
time_diff = stop - start

run_time = str(datetime.timedelta(seconds=time_diff))

print()
print('-'*50)
print('AUSPOS_submission.py Summary Report')
print('-'*50)
print()
print(' Completed in {:s}'.format(run_time[:-4]))
print()
print(' {:d} files submitted'.format(submitted_count))
print()
print(' See {:s}'.format(results_file))
