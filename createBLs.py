#!/usr/bin/env python3

"""
NAME:
    createBLs.py
PURPOSE:
    Form baselines from the stations in a SINEX file and create DynaML
    formatted files
EXPLANATION:
    The code takes one or more SINEX files as input and returns, for each one,
    both a DynaML formatted station and measurement file for input into
    DynAdjust
USAGE:
    createBLs.py infile [infile...]
INPUT:
    One or more SINEX files. Wildcards may be used 
OUTPUT:
    One DynaML formatted station file and one DynaML formatted measurement file
    per input SINEX file. These files will have _stn.xml and _msr.xml appended
    to the root of the infile
HISTORY:
    0.01    2013-05-30  Craig Harrison
            - Written
    0.02    2013-06-21  Craig Harrison
            - Updated usage example
    0.03    2013-07-05  Craig Harrison
            - Fixed several bugs
    0.04    2013-09-10  Craig Harrison
            - Equation for creating baselines corrected
            - i.e., \Delta x_{12} = x_2 - x_1 NOT x_1 - x_2
    1.00    2015-01-16  Craig Harrison
            - Major re-write
            - Code renamed from sinex2dynaXML.py to createBLs.py
            - Removed core station
            - optparse (which is deprecated from 2.7) replaced with argparse
            - Removed bug in output file naming
    1.01    2015-05-06  Craig Harrison
            - Output baselines changed from measurement type G (single
                baseline) to type X (baseline cluster). This utilises the full
                VCV information
            - Default scale factor has been changed to 1 
    1.02    2015-08-28  Craig Harrison
            - Changed scaling to modify vscale rather than the actual
                uncertainties
    1.03    2016-01-29  Craig Harrison
            - Added <Source> and <ReferenceFrame> tags to the measurement file
    1.04    2016-04-11  Craig Harrison
            - Added the ability to specify v-scale using the results out from
                getSigma0.old.pl
    2.00    2016-07-31  Craig Harrison
            - Re-write due to move from NCI to GA, e.g., argparse was removed
            - Re-write to account for the new APREF solution, which requires
                that the SINEX files be converted to DynaML files before
                running getSigma0.pl
            - Incorporated renaming of APREF stations with discontinuities
    2.01    2016-11-23  Craig Harrison
            - Fixed bug where the a priori coordinates for APREF stations with
                discontinuities were being taken from the GDA2020 APREF
                solution
    3.00    2020-08-26 Craig Harrison
            - Refactor for Python 3
            - Generalised for inclusion in datum-modernisation repo
"""
import argparse
import os
import datetime
import re
import numpy as np


# Set up argparse
refFrames = ['GDA94', 'GDA2020', 'ITRF2014', 'ITRF2008', 'ITRF2005',
             'ITRF2000', 'ITRF97', 'ITRF96', 'ITRF94', 'ITRF93', 'ITRF92',
             'ITRF91', 'ITRF90', 'ITRF89', 'ITRF88', 'WGS84']
parser = argparse.ArgumentParser(
    description='Convert a SINEX file into a DynaML GNSS baseline cluster',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('-r', metavar='reference frame', dest='refFrame', type=str,
                    default='ITRF2014', choices=refFrames,
                    help='The reference frame of the SINEX file')
parser.add_argument('files', nargs='+',
                    help='The SINEX file to be converted')
args = parser.parse_args()

# Loop over the input files
for inputFile in args.files:
    print(inputFile)

    # Get root name of the SINEX file and open the output files
    rootName = os.path.basename(inputFile)
    rootName = rootName.split('.')[0]
    stn = open(rootName + '_stn.xml', 'w')
    msr = open(rootName + '_msr.xml', 'w')

    # Open the SINEX file and read in all lines
    snxFile = open(inputFile)
    lines = snxFile.readlines()

    # Create lists to hold the site ID, station coordinate estimate, and the
    # VCV matrix lines
    estimateLines = []
    matrixLines = []
    goE = 0
    goM = 0
    for line in lines:
        if re.match('\+SOLUTION/ESTIMATE', line):
            goE = 1
        if re.match('\+SOLUTION/MATRIX_ESTIMATE', line):
            goM = 1
        if goE and not re.match('[+*-]', line):
            estimateLines.append(line)
        if goM and not re.match('[+*-]', line):
            matrixLines.append(line)
        if re.match('-SOLUTION/ESTIMATE', line):
            goE = 0
        if re.match('-SOLUTION/MATRIX_ESTIMATE', line):
            goM = 0

    # Get the yearDoy and epoch
    year = int(estimateLines[0][27:29])
    if year < 94:
        year += 2000
    else:
        year += 1900
    doy = int(estimateLines[0][30:33])
    date = datetime.date(year, 1, 1)
    date = date + datetime.timedelta(days=doy)
    epoch = date.strftime('%d.%m.%Y')

    # Write headers
    stn.write('<?xml version="1.0"?>\n')
    stn.write('<DnaXmlFormat type="Station File" referenceframe="' +
              args.refFrame + '" epoch="' + epoch +
              '" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
              'xsi:noNamespaceSchemaLocation="DynaML.xsd">\n')

    msr.write('<?xml version="1.0"?>\n')
    msr.write('<DnaXmlFormat type="Measurement File" referenceframe="' +
              args.refFrame + '" epoch="' + epoch +
              '" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
              'xsi:noNamespaceSchemaLocation="DynaML.xsd">\n')

    # Create a list of dictionaries to hold the station names and their
    # coordinates
    stats = []
    data = []
    estimateLines.reverse()
    while estimateLines:
        col = estimateLines.pop().rstrip().split()
        source = {}
        stats.append(col[2].upper())
        source['site'] = col[2].upper()
        source['x'] = float(col[8])
        col = estimateLines.pop().rstrip().split()
        source['y'] = float(col[8])
        col = estimateLines.pop().rstrip().split()
        source['z'] = float(col[8])
        data.append(source)
    print('len data:', len(data))

    # Create the variance-covariance matrix. In the SINEX file it is given as
    # a lower triangular matrix
    vcvL = np.array(np.zeros((3 * len(data), 3 * len(data))))
    for line in matrixLines:
        col = line.rstrip().split()
        for i in range(2, len(col)):
            vcvL[int(col[0]) - 1, int(col[1]) + i - 3] = float(col[i])
    vcvU = np.copy(vcvL.transpose())
    for i in range(3 * len(data)):
        vcvU[i, i] = 0
    vcv = vcvL + vcvU
    print('vcv:', vcv.shape)

    # Create the design matrix
    desMatrix = np.array(np.zeros((3 * (len(data) - 1), 3 * len(data))))
    for i in range(len(data) - 1):
        desMatrix[3 * i, 0] = -1
        desMatrix[3 * i + 1, 1] = -1
        desMatrix[3 * i + 2, 2] = -1
        desMatrix[3 * i, 3 * (i + 1)] = 1
        desMatrix[3 * i + 1, 3 * (i + 1) + 1] = 1
        desMatrix[3 * i + 2, 3 * (i + 1) + 2] = 1
    print('design matrix:', desMatrix.shape)

    # Create the matrix of observed antenna positions
    coords = np.array(np.zeros((3 * len(data), 1)))
    for i in range(len(data)):
        coords[3 * i, 0] = data[i]['x']
        coords[3 * i + 1, 0] = data[i]['y']
        coords[3 * i + 2, 0] = data[i]['z']
    print('coordinates:', coords.shape)

    # Calculate the deltas and the corresponding VCV matrix
    deltas = desMatrix @ coords
    delVCV = desMatrix @ vcv @ desMatrix.transpose()
    print('deltas:', deltas.shape)
    print('delVCV:', delVCV.shape)

    # Loop over the sites and write the station data to the output XML file
    for i in range(len(data)):
        stn.write('\t<DnaStation>\n')
        stn.write('\t\t<Name>%s</Name>\n' % (data[i]['site']))
        stn.write('\t\t<Constraints>FFF</Constraints>\n')
        stn.write('\t\t<Type>XYZ</Type>\n')
        stn.write('\t\t<StationCoord>\n')
        stn.write('\t\t\t<Name>%s</Name>\n' % (data[i]['site']))
        stn.write('\t\t\t<XAxis>%20.14e</XAxis>\n' % (data[i]['x']))
        stn.write('\t\t\t<YAxis>%20.14e</YAxis>\n' % (data[i]['y']))
        stn.write('\t\t\t<Height>%20.14e</Height>\n' % (data[i]['z']))
        stn.write('\t\t\t<HemisphereZone></HemisphereZone>\n')
        stn.write('\t\t</StationCoord>\n')
        stn.write('\t\t<Description></Description>\n')
        stn.write('\t</DnaStation>\n')

    # Write the measurement data to the output XML file
    msr.write('\t<!--Type X GNSS baseline cluster (full correlations)-->\n')
    msr.write('\t<DnaMeasurement>\n')
    msr.write('\t\t<Type>X</Type>\n')
    msr.write('\t\t<Ignore/>\n')
    msr.write('\t\t<ReferenceFrame>%s</ReferenceFrame>\n' % args.refFrame)
    msr.write('\t\t<Epoch>%s</Epoch>\n' % epoch)
    msr.write('\t\t<Vscale>1.000</Vscale>\n')
    msr.write('\t\t<Pscale>1.000</Pscale>\n')
    msr.write('\t\t<Lscale>1.000</Lscale>\n')
    msr.write('\t\t<Hscale>1.000</Hscale>\n')
    msr.write('\t\t<Total>%s</Total>\n' % (len(data) - 1))
    numCovar = len(data) - 2
    for i in range(len(data)-1):
        msr.write('\t\t<First>%s</First>\n' % (data[0]['site']))
        msr.write('\t\t<Second>%s</Second>\n' % (data[i+1]['site']))
        msr.write('\t\t<GPSBaseline>\n')
        msr.write('\t\t\t<X>%20.14e</X>\n' % (deltas[3 * i, 0]))
        msr.write('\t\t\t<Y>%20.14e</Y>\n' % (deltas[3 * i + 1, 0]))
        msr.write('\t\t\t<Z>%20.14e</Z>\n' % (deltas[3 * i + 2, 0]))
        msr.write('\t\t\t<SigmaXX>%20.14e</SigmaXX>\n' %
                  (delVCV[3 * i, 3 * i]))
        msr.write('\t\t\t<SigmaXY>%20.14e</SigmaXY>\n' %
                  (delVCV[3 * i + 1, 3 * i]))
        msr.write('\t\t\t<SigmaXZ>%20.14e</SigmaXZ>\n' %
                  (delVCV[3 * i + 2, 3 * i]))
        msr.write('\t\t\t<SigmaYY>%20.14e</SigmaYY>\n' %
                  (delVCV[3 * i + 1, 3 * i + 1]))
        msr.write('\t\t\t<SigmaYZ>%20.14e</SigmaYZ>\n' %
                  (delVCV[3 * i + 2, 3 * i + 1]))
        msr.write('\t\t\t<SigmaZZ>%20.14e</SigmaZZ>\n' %
                  (delVCV[3 * i + 2, 3 * i + 2]))
        for j in range(numCovar):
            print(i, j)
            msr.write('\t\t\t<GPSCovariance>\n')
            msr.write('\t\t\t\t<m11>%20.14e</m11>\n' %
                      (delVCV[3 * (i + 1) + 3 * j, 3 * i]))
            print(3 * (i + 1) + 3 * j, 3 * i)
            msr.write('\t\t\t\t<m12>%20.14e</m12>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 1, 3 * i]))
            print(3 * (i + 1) + 3 * j + 1, 3 * i)
            msr.write('\t\t\t\t<m13>%20.14e</m13>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 2, 3 * i]))
            print(3 * (i + 1) + 3 * j + 2, 3 * i)
            msr.write('\t\t\t\t<m21>%20.14e</m21>\n' %
                      (delVCV[3 * (i + 1) + 3 * j, 3 * i + 1]))
            print(3 * (i + 1) + 3 * j, 3 * i + 1)
            msr.write('\t\t\t\t<m22>%20.14e</m22>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 1, 3 * i + 1]))
            print(3 * (i + 1) + 3 * j + 1, 3 * i + 1)
            msr.write('\t\t\t\t<m23>%20.14e</m23>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 2, 3 * i + 1]))
            print(3 * (i + 1) + 3 * j + 2, 3 * i + 1)
            msr.write('\t\t\t\t<m31>%20.14e</m31>\n' %
                      (delVCV[3 * (i + 1) + 3 * j, 3 * i + 2]))
            print(3 * (i + 1) + 3 * j, 3 * i + 2)
            msr.write('\t\t\t\t<m32>%20.14e</m32>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 1, 3 * i + 2]))
            print(3 * (i + 1) + 3 * j + 1, 3 * i + 2)
            msr.write('\t\t\t\t<m33>%20.14e</m33>\n' %
                      (delVCV[3 * (i + 1) + 3 * j + 2, 3 * i + 2]))
            print(3 * (i + 1) + 3 * j + 2, 3 * i + 2)
            msr.write('\t\t\t</GPSCovariance>\n')
        numCovar -= 1
        msr.write('\t\t</GPSBaseline>\n')
    msr.write('\t\t<Source>%s</Source>\n' % os.path.basename(inputFile))
    msr.write('\t</DnaMeasurement>\n')
    stn.write('</DnaXmlFormat>\n')
    msr.write('</DnaXmlFormat>\n')
