#!/usr/bin/env python

'''
### NEED TO ADD ###

Craig

When you create the NGCA DynaNet stn and msr files would it be possible to 
include the following elements for the GPS Baseline Cluster measurements.

<AtDate>                - Start and end epochs (yyyy-mm-ddThh:mm:ss) for 
                            cluster measurement.  Currently in SINEX header?
<ToDate>

The start and end epochs of the measurement give you the duration that could be useful when determining scalars for the baseline clusters.
'''

'''
NAME:
    createBLs.py
PURPOSE:
    Form baselines from the stations in a SINEX file and create DynaML
    formatted files
EXPLANATION:
    The code takes one or more SINEX files as input and returns both a DynaML
    formatted station and measurement file for input into DynaNet
USAGE:
    createBLs.py -c CORESTATION -r ROOTNAME -s SCALEFACTOR infile [infile...]
    createBLs.py -h for more information
    createBLs.py --version for version information
INPUT:
    One or more SINEX files. Wildcards may be used 
OUTPUT:
    One dynaML formatted station file and one dynaML formatted measurement file
    The output files will be named ROOTstn.xml and ROOTmsr.xml 
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
            - OUtput baselines changed from measurement type G (single baseline)
                to type X (baseline cluster). This utilises the full VCV
                information
            - Default scale factor has been changed to 1 
    1.02    2015-08-28  Craig Harrison
            - Changed scaling to modify vscale rather than the actual
                uncertainties
    1.03    2016-01-29  Craig Harrison
            - Added <Source> and <ReferenceFrame> tags to the measurement file
    1.04    2016-04-11  Craig Harrison
            - Added the ability to specify v-scale using the results out from
                getSigma0.old.pl
'''
import sys
import re
import argparse
from numpy import matrix, zeros, copy

# Create an ArgumentParser object
parser = argparse.ArgumentParser( 
    description='Create baselines from one or more SINEX files.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

# Add the arguments and parse the command line
parser.add_argument(
    '-c', '--coreStation', help=
    'the station from which all baselines are calculated')
parser.add_argument(
    '-r', '--rootName', default='output', help=
    'root name for the two output files, ROOTstn.xml and ROOTmsr.xml')
parser.add_argument(
    '-s', '--scaleFactor', default=1, type=int, help='the VCV scale factor')
parser.add_argument('infile', nargs='+', help='the SINEX files to be processed')
parser.add_argument('--version', action='version', version='%(prog)s 1.04')
args = parser.parse_args()
if args.coreStation:
    args.coreStation = args.coreStation.upper()

# Open the output files
stn = open(args.rootName + 'stn.xml', 'w')
msr = open(args.rootName + 'msr.xml', 'w')

# Write headers
stnHead = '''<?xml version="1.0"?>
<DnaXmlFormat type="Station File" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="DynaML.xsd">
'''
stn.write(stnHead)
msrHead = '''<?xml version="1.0"?>
<DnaXmlFormat type="Measurement File" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="DynaML.xsd">
'''
msr.write(msrHead)

# Set some variables
refFrame = 'GDA94'
epoch = '01.01.1994'

seen = [] # Station name list; ensures no duplicates in stn.xml

# Loop over the input files
for inputFile in args.infile:

# Open the adj file and get sigma0
    col = inputFile.split('.')
    adjFile = open(col[0] + '.simult.adj')
    adjLines = adjFile.readlines()
    for adjLine in adjLines:
        if re.match('Rigorous Sigma Zero', adjLine):
            [x1, x2, x3, sigma0] = adjLine.rstrip().split()
            sigma0 = float(sigma0)
            break

# Open the SINEX file and read in all lines
    sinexFile = open(inputFile)
    lines = sinexFile.readlines()

# Create lists to hold the site ID, station coordinate estimate, and the VCV 
# matrix lines
    estimateLines = []
    matrixLines = []
    goE = 0
    goM = 0
    for line in lines:
        if re.match('\+SOLUTION/ESTIMATE',line):
            goE = 1
        if re.match('\+SOLUTION/MATRIX_ESTIMATE',line):
            goM = 1
        if goE:
            if not re.match('\+|\*|\-',line):
                estimateLines.append(line)
        if goM:
            if not re.match('\+|\*|\-',line):
                matrixLines.append(line)
        if re.match('\-SOLUTION/ESTIMATE',line):
            goE = 0
        if re.match('\-SOLUTION/MATRIX_ESTIMATE',line):
            goM = 0

# Create a list of dictionaries to hold the station names and their coordinates
    data = []
    estimateLines.reverse()
    while estimateLines:
        col = estimateLines.pop().rstrip().split()
        source = {}
        source['site'] = col[2].upper()
        source['x'] = float(col[8])
        col = estimateLines.pop().rstrip().split()
        source['y'] = float(col[8])
        col = estimateLines.pop().rstrip().split()
        source['z'] = float(col[8])
        data.append(source)

# Create the variance-covariance matrix. In the SINEX file it is given as a
# lower triangular matrix
    vcvL = matrix(zeros((3*len(data), 3*len(data))))
    for line in matrixLines:
        col = line.rstrip().split()
        for i in range(2, len(col)):
            vcvL[int(col[0])-1, int(col[1])+i-3] = float(col[i])
    vcvU = copy(vcvL.transpose())
    for i in range(3*len(data)):
        vcvU[i, i] = 0
    vcv = vcvL + vcvU
#    vcv *= args.scaleFactor

# Set the index of the core station
    csFound = 0
    if args.coreStation:
        for i in range(len(data)):
            if data[i]['site'] == args.coreStation:
                csIndex = i
                csFound = 1
                coreStat = data[i]['site']
                break
        if not csFound:
            print ''
            print 'Your core station ' + args.coreStation + \
                  ' does not exist in the input file. Please check your '
            print 'station name and try again.'
            print ''
            sys.exit()
    else:
        csIndex=0
        coreStat = data[0]['site']

# Create the design matrix
    desMatrix = matrix(zeros((3*(len(data)-1), 3*len(data))))
    cnt = 0
    for i in range(len(data)-1):
        if (i == csIndex):
            cnt = 1
        desMatrix[3*i, 3*csIndex] = -1
        desMatrix[3*i+1, 3*csIndex+1] = -1
        desMatrix[3*i+2, 3*csIndex+2] = -1
        desMatrix[3*i, 3*(i+cnt)] = 1
        desMatrix[3*i+1, 3*(i+cnt)+1] = 1
        desMatrix[3*i+2, 3*(i+cnt)+2] = 1
                                                                    
# Create the matrix of observed antenna positions
    coords = matrix(zeros((3*len(data), 1)))
    for i in range(len(data)):
        coords[3*i, 0] = data[i]['x']
        coords[3*i+1, 0] = data[i]['y']
        coords[3*i+2, 0] = data[i]['z']
                                                                                # Calculate the deltas and the corresponding VCV matrix
    deltas = desMatrix * coords
    delVCV = desMatrix * vcv * desMatrix.transpose()
                                                                                # Loop over the sites and write the station data to the output XML file. Skip
# stations that have already been seen
    for i in range(len(data)):
        if data[i]['site'] not in seen:
            seen.append(data[i]['site'])
            stn.write('\t<DnaStation>\n')
            stn.write('\t\t<Name>%s</Name>\n'%(data[i]['site']))
            stn.write('\t\t<Constraints>FFF</Constraints>\n')
            stn.write('\t\t<Type>XYZ</Type>\n')
            stn.write('\t\t<StationCoord>\n')
            stn.write('\t\t\t<Name>%s</Name>\n'%(data[i]['site']))
            stn.write('\t\t\t<XAxis>%20.14e</XAxis>\n'%(data[i]['x']))
            stn.write('\t\t\t<YAxis>%20.14e</YAxis>\n'%(data[i]['y']))
            stn.write('\t\t\t<Height>%20.14e</Height>\n'%(data[i]['z']))
            stn.write('\t\t\t<HemisphereZone></HemisphereZone>\n')
            stn.write('\t\t</StationCoord>\n')
            stn.write('\t\t<Description></Description>\n')
            stn.write('\t</DnaStation>\n')

# Create an array of the stations minus the core station
    nonCoreStns = []
    for i in range(len(data)):
        if i != csIndex:
            nonCoreStns.append(data[i]['site'])
    numCovar = len(nonCoreStns) - 1
    if numCovar < 0:
        print inputFile

# Loop over the non-core stations and write the measurement data to the output
# XML file
    msr.write('\t<!--Type X GNSS baseline cluster (full correlations)-->\n')
    msr.write('\t<DnaMeasurement>\n')
    msr.write('\t\t<Type>X</Type>\n')
    msr.write('\t\t<Ignore/>\n')
    msr.write('\t\t<ReferenceFrame>%s</ReferenceFrame>\n'%(refFrame))
    msr.write('\t\t<Epoch>%s</Epoch>\n'%(epoch))
    msr.write('\t\t<Vscale>%.3f</Vscale>\n'%(sigma0))
    msr.write('\t\t<Pscale>1.000</Pscale>\n')
    msr.write('\t\t<Lscale>1.000</Lscale>\n')
    msr.write('\t\t<Hscale>1.000</Hscale>\n')
    msr.write('\t\t<Total>%s</Total>\n'%(len(nonCoreStns)))
    for i in range(len(nonCoreStns)):
        msr.write('\t\t<First>%s</First>\n'%(coreStat))
        msr.write('\t\t<Second>%s</Second>\n'%(nonCoreStns[i]))
        msr.write('\t\t<GPSBaseline>\n')
        msr.write('\t\t\t<X>%20.14e</X>\n'%(deltas[3*i, 0]))
        msr.write('\t\t\t<Y>%20.14e</Y>\n'%(deltas[3*i+1, 0]))
        msr.write('\t\t\t<Z>%20.14e</Z>\n'%(deltas[3*i+2, 0]))
        msr.write('\t\t\t<SigmaXX>%20.14e</SigmaXX>\n'%(delVCV[3*i, 3*i]))
        msr.write('\t\t\t<SigmaXY>%20.14e</SigmaXY>\n'%(delVCV[3*i+1, 3*i]))
        msr.write('\t\t\t<SigmaXZ>%20.14e</SigmaXZ>\n'%(delVCV[3*i+2, 3*i]))
        msr.write('\t\t\t<SigmaYY>%20.14e</SigmaYY>\n'%(delVCV[3*i+1, 3*i+1]))
        msr.write('\t\t\t<SigmaYZ>%20.14e</SigmaYZ>\n'%(delVCV[3*i+2, 3*i+1]))
        msr.write('\t\t\t<SigmaZZ>%20.14e</SigmaZZ>\n'%(delVCV[3*i+2, 3*i+2]))
        for j in range(numCovar):
            msr.write('\t\t\t<GPSCovariance>\n')
            msr.write('\t\t\t\t<m11>%20.14e</m11>\n'%(delVCV[3*(i+1)+3*j, 3*i]))
            msr.write('\t\t\t\t<m12>%20.14e</m12>\n'%(delVCV[3*(i+1)+3*j+1, 3*i]))
            msr.write('\t\t\t\t<m13>%20.14e</m13>\n'%(delVCV[3*(i+1)+3*j+2, 3*i]))
            msr.write('\t\t\t\t<m21>%20.14e</m21>\n'%(delVCV[3*(i+1)+3*j, 3*i+1]))
            msr.write('\t\t\t\t<m22>%20.14e</m22>\n'%(delVCV[3*(i+1)+3*j+1, 3*i+1]))
            msr.write('\t\t\t\t<m23>%20.14e</m23>\n'%(delVCV[3*(i+1)+3*j+2, 3*i+1]))
            msr.write('\t\t\t\t<m31>%20.14e</m31>\n'%(delVCV[3*(i+1)+3*j, 3*i+2]))
            msr.write('\t\t\t\t<m32>%20.14e</m32>\n'%(delVCV[3*(i+1)+3*j+1, 3*i+2]))
            msr.write('\t\t\t\t<m33>%20.14e</m33>\n'%(delVCV[3*(i+1)+3*j+2, 3*i+2]))
            msr.write('\t\t\t</GPSCovariance>\n')
        numCovar -= 1
        msr.write('\t\t</GPSBaseline>\n')
    msr.write('\t\t<Source>%s</Source>\n'%inputFile)
    msr.write('\t</DnaMeasurement>\n')
stn.write('</DnaXmlFormat>\n')
msr.write('</DnaXmlFormat>\n')
