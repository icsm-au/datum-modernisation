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
    The code takes one or more SINEX files as input and returns, for each one,
    both a DynaML formatted station and measurement file for input into DynaNet
USAGE:
    createBLs.py infile [infile...]
INPUT:
    One or more SINEX files. Wildcards may be used 
OUTPUT:
    One dynaML formatted station file and one dynaML formatted measurement file
    per input SINEX file. These files shall have stn.xml and msr.xml appended
    to the root
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
    2.00    2016-07-31  Craig Harrison
            - Re-write due to move from NCI to GA, e.g., argparse was removed
            - Re-write to account for the new APREF solution, which requires
                that the SINEX files be comverted to DynaML files before
                running getSigma0.pl
            - Incorporated renaming of APREF stations with discontinuities
    2.01    2016-11-23  Craig Harrison
            - Fixed bug where the a priori coordinates for APREF stations with
                discontinuities were being taken from the GDA2020 APREF
                solution
'''
import sys, os, datetime, re 
from glob import glob
from numpy import matrix, zeros, copy

# Move to jurisdiction's directory
jur = sys.argv[1]
os.chdir('/nas/users/u74392/unix/gda2020Data/ngca/' + jur)

# Check that the necessary directories exist
if not os.path.isdir('rinexantls'):
    sys.exit('Please check your current directory: rinexantls/ does not exist')
if not os.path.isdir('sinexFiles'):
    sys.exit('Please check your current directory: sinexFiles/ does not exist')
if not os.path.isdir('baselines'):
    sys.exit('Please check your current directory: baselines/ does not exist')

# Set some variables
refFrame = 'ITRF2014'

# Delete the old baselines
print '* Deleting all existing baselines'
for file in glob('baselines/*'):
    os.remove(file)

# Read in the discontinuity information for renaming purposes
disconts = {}
stnsWdiscont = set()
cwd = os.getcwd()
os.chdir('/nas/gemd/geodesy_data/gnss/archive_GDA2020/apref/')
for discontFile in glob('apref*.disconts'):
    pass
for line in open(discontFile):
    if line[4] == '_':
        stn = line[0:4]
        stnsWdiscont.add(stn)
        try:
            disconts[stn]
        except KeyError:
            disconts[stn] = []
        yearDoy = line[5:12]
        disconts[stn].append(yearDoy)
os.chdir(cwd)

# Loop over the input files
print '* Creating a baseline cluster for every file in sinexFiles/'
for inputFile in glob('sinexFiles/*'):
    print inputFile
    
# Get the yearDoy and epoch
    rootName = os.path.basename(inputFile)
    rootName = rootName.replace('.SNX.' + jur.upper() + '.NGCA', '')
    rootName = rootName.replace('.SNX.AUS', '_all')
    yyDoy = rootName[:5]
    if int(yyDoy) < 94000:
        yearDoy = '20' + yyDoy
    else:
        yearDoy = '19' + yyDoy
    year = int(yearDoy[0:4])
    doy = int(yearDoy[4:7]) - 1
    date = datetime.date(year, 1, 1)
    date = date + datetime.timedelta(days=doy)
    epoch = date.strftime('%d.%m.%Y')

# Open the output files
    stn = open(rootName + '_stn.xml', 'w')
    msr = open(rootName + '_msr.xml', 'w')

# Write headers
    stn.write('<?xml version="1.0"?>\n')
    stn.write('<DnaXmlFormat type="Station File" referenceframe="' +
                refFrame + '" epoch="' + epoch + 
                '" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
                'xsi:noNamespaceSchemaLocation="DynaML.xsd">\n')

    msr.write('<?xml version="1.0"?>\n')
    msr.write('<DnaXmlFormat type="Measurement File" referenceframe="' +
                refFrame + '" epoch="' + epoch +
                '" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
                'xsi:noNamespaceSchemaLocation="DynaML.xsd">\n')

# Open the SINEX file and read in all lines
    snxFile = open(inputFile)
    lines = snxFile.readlines()

# Create lists to hold the site ID, station coordinate estimate, and the VCV 
# matrix lines
    estimateLines = []
    matrixLines = []
    goE = 0
    goM = 0
    for line in lines:
        if re.match('\+SOLUTION/ESTIMATE', line):
            goE = 1
        if re.match('\+SOLUTION/MATRIX_ESTIMATE', line):
            goM = 1
        if goE:
            if not re.match('\+|\*|\-', line):
                estimateLines.append(line)
        if goM:
            if not re.match('\+|\*|\-', line):
                matrixLines.append(line)
        if re.match('\-SOLUTION/ESTIMATE', line):
            goE = 0
        if re.match('\-SOLUTION/MATRIX_ESTIMATE', line):
            goM = 0

# Create a list of dictionaries to hold the station names and their coordinates
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

# Open the corresponding RINEX antenna information file & set the core station
    rootName = rootName.replace('_all', '')
    if len(rootName) == 5:
        rinexAntLs = rootName + '_ls'
    else:
        rinexAntLs = rootName.replace('_', '') + '_ls'
    rinexAntLs = 'rinexantls/' + rinexAntLs
    coreStation = ''
    for line in open(rinexAntLs):
        stat = line[0:4]
        if stat.upper() in stats:
            coreStation = stat.upper()
            break
    if not coreStation:
        sys.exit('No core station set')
        
# Set the index of the core station
    for i in range(len(data)):
        if data[i]['site'] == coreStation:
            csIndex = i
            break

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

# Loop over the sites and write the station data to the output XML file
    for i in range(len(data)):
        
# Check if station has a discontinuity and, if so, rename it
        if data[i]['site'] in stnsWdiscont:
            discnts = disconts[data[i]['site']][:]
            discnts.sort()
            discnts.reverse()
            if yearDoy <= min(discnts):
                discnt = min(discnts)
                label = data[i]['site'] + '_' + discnt
                data[i]['site'] = label
            else:
                for discnt in discnts:
                    if discnt < yearDoy:
                        label = data[i]['site'] + '_' + discnt
                        data[i]['site'] = label
                        break

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

# Loop over the non-core stations and write the measurement data to the output
# XML file
    msr.write('\t<!--Type X GNSS baseline cluster (full correlations)-->\n')
    msr.write('\t<DnaMeasurement>\n')
    msr.write('\t\t<Type>X</Type>\n')
    msr.write('\t\t<Ignore/>\n')
    msr.write('\t\t<ReferenceFrame>%s</ReferenceFrame>\n'%(refFrame))
    msr.write('\t\t<Epoch>%s</Epoch>\n'%(epoch))
    msr.write('\t\t<Vscale>1.000</Vscale>\n')
    msr.write('\t\t<Pscale>1.000</Pscale>\n')
    msr.write('\t\t<Lscale>1.000</Lscale>\n')
    msr.write('\t\t<Hscale>1.000</Hscale>\n')
    msr.write('\t\t<Total>%s</Total>\n'%(len(nonCoreStns)))
    for i in range(len(nonCoreStns)):
        
# Check if station has a discontinuity and, if so, rename it
        if nonCoreStns[i] in stnsWdiscont:
            discnts = disconts[nonCoreStns[i]][:]
            discnts.reverse()
            if yearDoy <= min(discnts):
                discnt = min(discnts)
                nonCoreStns[i] = nonCoreStns[i] + '_' + discnt
            else:
                for discnt in discnts:
                    if discnt < yearDoy:
                        nonCoreStns[i] = nonCoreStns[i] + '_' + discnt
                        break

        msr.write('\t\t<First>%s</First>\n'%(coreStation))
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
            msr.write('\t\t\t\t<m11>%20.14e</m11>\n'% \
                (delVCV[3*(i+1)+3*j, 3*i]))
            msr.write('\t\t\t\t<m12>%20.14e</m12>\n'% \
                (delVCV[3*(i+1)+3*j+1, 3*i]))
            msr.write('\t\t\t\t<m13>%20.14e</m13>\n'% \
                (delVCV[3*(i+1)+3*j+2, 3*i]))
            msr.write('\t\t\t\t<m21>%20.14e</m21>\n'% \
                (delVCV[3*(i+1)+3*j, 3*i+1]))
            msr.write('\t\t\t\t<m22>%20.14e</m22>\n'% \
                (delVCV[3*(i+1)+3*j+1, 3*i+1]))
            msr.write('\t\t\t\t<m23>%20.14e</m23>\n'% \
                (delVCV[3*(i+1)+3*j+2, 3*i+1]))
            msr.write('\t\t\t\t<m31>%20.14e</m31>\n'% \
                (delVCV[3*(i+1)+3*j, 3*i+2]))
            msr.write('\t\t\t\t<m32>%20.14e</m32>\n'% \
                (delVCV[3*(i+1)+3*j+1, 3*i+2]))
            msr.write('\t\t\t\t<m33>%20.14e</m33>\n'% \
                (delVCV[3*(i+1)+3*j+2, 3*i+2]))
            msr.write('\t\t\t</GPSCovariance>\n')
        numCovar -= 1
        msr.write('\t\t</GPSBaseline>\n')
    msr.write('\t\t<Source>%s</Source>\n'%os.path.basename(inputFile))
    msr.write('\t</DnaMeasurement>\n')
    stn.write('</DnaXmlFormat>\n')
    msr.write('</DnaXmlFormat>\n')

for file in glob('*.xml'):
    os.rename(file, 'baselines/' + file)

print '*** Change to using epoch in SINEX file rather than the filename'
