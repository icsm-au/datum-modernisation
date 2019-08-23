# ----------------------------------------------------------------------
# AUSPOS_fetch.py
# ----------------------------------------------------------------------
# Author:   Nicholas Gowans
# Date:     23 AUG 2019
# Purpose:  To read output from AUSPOS_submission.py, and retrieve the
#           AUSPOS .snx and .pdf results from the ftp server.
# ----------------------------------------------------------------------
# Usage:    CMD:\>python AUSPOS_fetch.py <AUSPOS_submission.py_results.csv>
# ----------------------------------------------------------------------
# Notes:
# ----------------------------------------------------------------------

import os
import ftplib
import shutil
import time
import timeit
import datetime

start = timeit.default_timer()

# ----------------------------------------------------------------------
# Consume AUSPOS_submission results
# ----------------------------------------------------------------------
results_name = os.sys.argv[1]

results_dict = {}

results_fh = open(results_name, 'r')

# read input file to dictionary
for line in results_fh:
    items = line.split(',')
    rnx_file = items[0]
    HI = items[1]
    ant = items[2]
    job_ref = items[3].strip()

    results_dict[rnx_file] = {
        'HI': HI,
        'ant': ant,
        'job_ref': job_ref
    }


# ----------------------------------------------------------------------
# Create results directory
# ----------------------------------------------------------------------

results_dir = 'AUSPOS_fetch'

# check if directory already exists, prompt user to delete
if os.path.isdir(results_dir):
    print('')
    print(' *** AUSPOS_fetch directory exists already ***')
    answer = input(' Delete and continue? Y/N\n  ')

    if answer.upper() == 'Y':
        shutil.rmtree(results_dir, ignore_errors=True)
        time.sleep(2)
    else:
        print()
        print(' Exiting script...')
        print()
        exit()

os.mkdir(results_dir)
os.chdir(results_dir)


# ----------------------------------------------------------------------
# Connect to ftp and search for AUSPOS results
# ----------------------------------------------------------------------

# initialise counters
sessionsFd = 0
sessionsNotFd = 0

# connect to ftp
ftp = ftplib.FTP('ftp.ga.gov.au')
ftp.login()
AUSPOS_address = 'geodesy-outgoing/apps/ausposV2/'
ftp.cwd(AUSPOS_address)

# retrieve results and move to relevant folders
for s in results_dict:

    # create sub-directory for each session
    job_ref = results_dict[s]['job_ref'][-4:]

    directoryName = '{:s}_{:s}'.format(s, job_ref)

    os.mkdir(directoryName)
    os.chdir(directoryName)

    # look for results on ftp, else rename local directory as not found
    try:
        ftp.cwd(job_ref)
        sessionsFd += 1
    except:
        sessionsNotFd += 1
        os.chdir('..')
        os.rename(directoryName, directoryName + '_ftp_notFound')

    # create listing of ftp files
    ftp_data = []
    ftp.dir(ftp_data.append)

    # sift through ftp listing, and download snx and pdf files
    for line in ftp_data:
        ftp_file = line[55:].strip()

        if '.SNX' in ftp_file:
            ftp.retrbinary('RETR ' + ftp_file, open(ftp_file, 'wb').write)

        elif '.pdf' in ftp_file:
            pdf_name = s + '_AUSPOS_Report.pdf'
            ftp.retrbinary('RETR ' + ftp_file, open(pdf_name, 'wb').write)

    # move back to parent directories
    ftp.cwd('..')
    os.chdir('..')


# ----------------------------------------------------------------------
# Print Summary
# ----------------------------------------------------------------------

stop = timeit.default_timer()
time_diff = stop - start

run_time = str(datetime.timedelta(seconds=time_diff))

print()
print('-'*50)
print(' AUSPOS_fetch.py Summary Report')
print('-'*50)
print()
print(' Completed in {:s}'.format(run_time[:-4]))
print()
print(' {:d} of {:d} session results retrieved successfully'.format(sessionsFd, len(results_dict)))
print()
