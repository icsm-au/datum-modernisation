#!/usr/bin/env python3

"""This script adds Type B uncertainties to those given in the .apu file.
"""

from sys import exit
from glob import glob
from numpy import matrix
from math import radians, sin, cos, sqrt, atan2, degrees


def dd2dms(dd):
    minutes, seconds = divmod(abs(dd) * 3600, 60)
    degrees, minutes = divmod(minutes, 60)
    dms = degrees + (minutes / 100) + (seconds / 10000)
    return dms if dd >= 0 else -dms            
                
def dms2dd(dms):
    degmin, seconds = divmod(abs(dms) * 1000, 10)
    degrees, minutes = divmod(degmin, 100)
    dd = degrees + (minutes / 60) + (seconds / 360)
    return dd if dms >= 0 else -dd
    
def rotation_matrix(lat, lon):
    """Returns the 3x3 rotation matrix for a given latitude and longitude
    (given in decimal degrees)
    See Section 4.2.3 of the DynaNet User's Guide v3.3
    """
    (rlat, rlon) = (radians(lat), radians(lon))
    rot_matrix = matrix(
        [[-sin(rlon), -sin(rlat)*cos(rlon), cos(rlat)*cos(rlon)],
        [cos(rlon), -sin(rlat)*sin(rlon), cos(rlat)*sin(rlon)],
        [0.0, cos(rlat), sin(rlat)]]
    )
    return rot_matrix

def vcv_cart2local(vcv_cart, lat, lon):
    """Transforms a 3x3 VCV from the Cartesian to the local reference frame
    See Section 4.4.1 of the DynaNet User's Guide v3.3
    """
    rot_matrix = rotation_matrix(lat, lon)
    vcv_local = rot_matrix.transpose() * vcv_cart * rot_matrix
    return vcv_local

def error_ellipse(vcv):
    """Calculate the semi-major axis, semi-minor axis, and the orientation of
    the error ellipse calculated from a 3x3 VCV
    See Section 7.3.3.1 of the DynaNet User's Guide v3.3
    """
    z = sqrt((vcv[0, 0] - vcv[1, 1])**2 + 4 * vcv[0, 1]**2)
    a = sqrt(0.5 * (vcv[0, 0] + vcv[1, 1] + z))
    b = sqrt(0.5 * (vcv[0, 0] + vcv[1, 1] - z))
    orientation = 90 - degrees(0.5 * atan2((2 * vcv[0, 1]),
    (vcv[0, 0] - vcv[1, 1])))
    return a, b, orientation

def circ_hz_pu(a, b):
    """Calculate the circularised horizontal PU(95%) from the semi-major and
    semi-minor axes
    """
    q0 = 1.960790
    q1 = 0.004071
    q2 = 0.114276
    q3 = 0.371625
    c = b / a
    k = q0 + q1 * c + q2 * c**2 + q3 * c**3
    r = a * k
    return r

# Determine the files to use 
apuFiles = glob('*.apu')
if (len(apuFiles) == 1):
    apuFile = apuFiles[0]
elif (len(apuFiles) == 0):
    exit('\nThere is no apu file to work on\n')
else:
    print('\nThere are multiple apu files:')
    i = 0
    for apuFile in apuFiles:
        i += 1
        print('\t' + str(i) + '\t' + apuFile)
    fileNum = input('Type the number of the file you want to check: ')
    if int(fileNum) < 1 or int(fileNum) > len(apuFiles):
        exit('Invalid response. Select a number between 1 and ' +
            str(len(apuFiles)))
    apuFile = apuFiles[int(fileNum) - 1]

# Set the Type B uncertainties
rvsE = 0.003
rvsN = 0.003
rvsU = 0.006
nonRvsE = 0.006
nonRvsN = 0.006
nonRvsU = 0.012

# Create a list of RVS stations
rvsStations = ['ALBY', 'ALIC_2011201', 'ANDA', 'ARMC', 'ARUB', 'BALA', 'BBOO',
        'BDLE', 'BDVL', 'BEEC', 'BING', 'BKNL', 'BNDY', 'BRO1', 'BROC', 'BULA',
        'BUR2', 'BURA', 'CEDU', 'CNBN', 'COEN', 'COOB', 'COOL', 'DARW_2003094',
        'DODA', 'EDSV', 'ESPA_2016055', 'EXMT', 'FLND', 'FROY', 'GABO', 'GASC',
        'HERN', 'HIL1_2006222', 'HNIS', 'HOB2_2004358', 'HUGH', 'HYDN', 'IHOE',
        'JAB2_2016065', 'JERV', 'JLCK', 'KALG', 'KARR_2013254', 'KAT1', 'KELN',
        'KGIS', 'KILK', 'KMAN', 'LAMB', 'LARR_2011062', 'LIAW', 'LKYA', 'LONA',
        'LORD_2014185', 'LURA', 'MAIN', 'MEDO', 'MOBS_2004358', 'MRO1', 'MTCV',
        'MTDN', 'MTEM', 'MTMA', 'MULG', 'NBRK', 'NCLF', 'NEBO', 'NHIL', 'NMTN',
        'NNOR_2012276', 'NORF', 'NORS', 'NSTA', 'NTJN', 'PARK', 'PERT_2012297',
        'PTHL', 'PTKL', 'PTLD_2012123', 'RAVN', 'RKLD', 'RNSP_2015349', 'RSBY',
        'SA45', 'SPBY_2011326', 'STNY', 'STR1_2003311', 'SYDN', 'TBOB', 'THEV',
        'TID1_2004348', 'TMBO', 'TOMP', 'TOOW', 'TOW2_2011266', 'TURO', 'UCLA',
        'WAGN', 'WALH', 'WARA', 'WILU', 'WLAL', 'WMGA', 'WWLG', 'XMIS_2014177',
        'YAR2_2013171', 'YEEL', 'YELO_2016082']

# Open output file
fout = open(apuFile + '.typeB', 'w')

# Read in the apu file
apuLines = []
i = 0
with open(apuFile) as f:
    for line in f:
        if line[:9] == 'Station  ':
            j = i + 2
        apuLines.append(line.rstrip())
        i += 1

# Print out the header info
for line in apuLines[:j]:
    fout.write(line + '\n')

# Loop over the .apu file and read in the uncertainty info
stations = []
hpLat = {}
hpLon = {}
lat = {}
lon = {}
hPU = {}
vPU = {}
semiMajor = {}
semiMinor = {}
orient = {}
xLine = {}
xVar = {}
xyCoVar = {}
xzCoVar = {}
yLine = {}
yVar = {}
yzCoVar = {}
zLine = {}
zVar = {}
for line in apuLines[j:]:
    cols = line.split()
    numCols = len(cols)
    if numCols == 2:
        yLine[station] = line
        yVar[station] = float(line[131:150].strip())
        yzCoVar[station] = float(line[150:].strip())
    elif numCols == 1:
        zLine[station] = line
        zVar[station] = float(line[150:].strip())
    else:
        station = line[:20].rstrip()
        stations.append(station)
        hpLat[station] = float(line[23:36])
        hpLon[station] = float(line[38:51])
        lat[station] = dms2dd(hpLat[station])
        lon[station] = dms2dd(hpLon[station])
        hPU[station] = float(line[51:62].strip())
        vPU[station] = float(line[62:73].strip())
        semiMajor[station] = float(line[73:86].strip())
        semiMinor[station] = float(line[86:99].strip())
        orient[station] = float(line[99:112].strip())
        xLine[station] = line[112:]
        xVar[station] = float(line[112:131].strip())
        xyCoVar[station] = float(line[131:150].strip())
        xzCoVar[station] = float(line[150:].strip())

# Create the full Cartesian VCV from the upper triangular
vcv_cart = {}
for stat in stations:
    vcv_cart[stat] = matrix([[xVar[stat], xyCoVar[stat], xzCoVar[stat]],
                             [xyCoVar[stat], yVar[stat], yzCoVar[stat]],
                             [xzCoVar[stat], yzCoVar[stat], zVar[stat]]
                            ])

# Loop over all the stations
for stat in stations:

    # Transform the XYZ VCV to ENU
    vcv_local = vcv_cart2local(vcv_cart[stat], lat[stat], lon[stat])
    
    # Add the Type B uncertainty
    if stat in rvsStations:
        vcv_local[0, 0] += rvsE**2
        vcv_local[1, 1] += rvsN**2
        vcv_local[2, 2] += rvsU**2
    else:
        vcv_local[0, 0] += nonRvsE**2
        vcv_local[1, 1] += nonRvsN**2
        vcv_local[2, 2] += nonRvsU**2
    
    # Calculate the semi-major axis, semi-minor axis and orientation, and
    # convert the orientation from deciaml degrees to HP notation
    a, b, orientation = error_ellipse(vcv_local)
    orientation = dd2dms(orientation)

    # Calculate the PUs
    hz_pu = circ_hz_pu(a, b)
    vt_pu = 1.96 * sqrt(vcv_local[2, 2])

    # Output the uncertainties
    line = '{:20}{:>16.9f}{:>15.9f}{:11.4f}{:11.4f}{:13.4f}{:13.4f}{:13.4f}'. \
            format(stat, hpLat[stat], hpLon[stat], hz_pu, vt_pu, a, b,
                    orientation)
    line += xLine[stat]
    fout.write(line + '\n')
    fout.write(yLine[stat] + '\n')
    fout.write(zLine[stat] + '\n')

