#-----------------------------------------------------------------------
#                          DynAdjust.py
#-----------------------------------------------------------------------
#  Author: Nicholas Gowans
#    Date: 22 May 2019
# Purpose: To add type B uncertainties to DynAdjust .apu and .xyz files.
#
# ----------------------------------------------------------------------
#   Usage: CMD:\> python DynAdjust_TypeB.py <*.adj_file> <*.apu_file> <*.xyz_file>
#
# ----------------------------------------------------------------------
#   Notes: Adapted from Craig Harrison's addTypeB_AWG.py script to work
#          for full VCV DynAdjust .apu files, .adj files, and xyz files.
#
#-----------------------------------------------------------------------

import sys
import os
import math as m
import geodepy
import geodepy.convert as gc
import geodepy.transform as gt
import numpy as np



def rotation_matrix(lat, lon):
    """Returns the 3x3 rotation matrix for a given latitude and longitude
    (given in decimal degrees)
    See Section 4.2.3 of the DynaNet User's Guide v3.3
    """
    rlat = m.radians(lat)
    rlon = m.radians(lon)
    rot_matrix = np.array(
        [[-m.sin(rlon), -m.sin(rlat)*m.cos(rlon), m.cos(rlat)*m.cos(rlon)],
        [m.cos(rlon), -m.sin(rlat)*m.sin(rlon), m.cos(rlat)*m.sin(rlon)],
        [0.0, m.cos(rlat), m.sin(rlat)]]
    )
    return rot_matrix

def vcv_cart2local(vcv_cart, lat, lon):
    """Transforms a 3x3 VCV from the Cartesian to the local reference frame
    See Section 4.4.1 of the DynaNet User's Guide v3.3
    """
    rot_matrix = rotation_matrix(lat, lon)
    rot_trans = np.array(np.transpose(rot_matrix))
    vcv_local = np.matmul(rot_trans, vcv_cart)
    vcv_local = np.matmul(vcv_local, rot_matrix)

    return vcv_local


def vcv_local2cart(vcv_local, lat, lon):
    """Transforms a 3x3 VCV from the Cartesian to the local reference frame
    See Section 4.4.1 of the DynaNet User's Guide v3.3
    """
    rot_matrix = rotation_matrix(lat, lon)
    rot_trans = np.array(np.transpose(rot_matrix))
    vcv_cart = np.matmul(rot_matrix, vcv_local)
    vcv_cart = np.matmul(vcv_cart, rot_trans)
    return vcv_cart

def error_ellipse(vcv):
    """Calculate the semi-major axis, semi-minor axis, and the orientation of
    the error ellipse calculated from a 3x3 VCV
    See Section 7.3.3.1 of the DynaNet User's Guide v3.3
    """
    z = m.sqrt((vcv[0, 0] - vcv[1, 1])**2 + 4 * vcv[0, 1]**2)
    a = m.sqrt(0.5 * (vcv[0, 0] + vcv[1, 1] + z))
    b = m.sqrt(0.5 * (vcv[0, 0] + vcv[1, 1] - z))
    orientation = 90 - m.degrees(0.5 * m.atan2((2 * vcv[0, 1]),
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

dateUpdated = '20190522'

adj_file = sys.argv[1]
apu_file = sys.argv[2]
xyz_file = sys.argv[3]

log_fh = open('DynAdjust_TypeB.log','w')

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


#---------------------------------------------------
#              read .apu and apply type B unc.
#---------------------------------------------------

apu_file_fh = open(apu_file,'r')
apu_typeB = open(apu_file + '.TypeB','w')
lineCount = 0
stnLine = False
StnLineNo = 100
header = False
stn_unc = {}
typeB_log = ''
warning_str = ''
headerLineCount = 0
rotate_vcv = True

for line in apu_file_fh:
    lineCount += 1
    cols = line.split()
    numCols = len(cols)

    # check for header lines. Append metadata if end of header, print if not.
    if line == '-' * 80 + '\n':
        headerLineCount += 1
        if headerLineCount == 2:
            print('Type B Uncertainties               3, 3, 6 mm for RVS '
                  'stations; 6, 6, 12 for non RVS stations. Applied by DynAdjust_TypeB.py '
                  '(version: {:s}).'.format(dateUpdated), file=apu_typeB)
            print(line, file=apu_typeB, end='')
            continue
        else:
            print(line, file=apu_typeB, end='')
            continue

    if line == '-'*169 + '\n':
        StnLineNo = lineCount + 1
        print(line, file=apu_typeB, end='')
        continue

    # Check variance matrix units. Don't rotate if ENU.
    if line[:35] == 'Variance matrix units              ':
        if line[35:] == 'ENU\n':
            rotate_vcv = False

    if lineCount >= StnLineNo:
        
        # copy line across for separate VCV block header info
        if line == '\n':
            print(line, file=apu_typeB, end='')
            continue
        if line[:6] == 'Block ':
            if len(line) < 20:
                print(line, file=apu_typeB, end='')
                continue
        if line[:36] == 'Station                     Latitude':
            print(line, file=apu_typeB, end='')
            continue
            
        # account for station names with spaces.
        temp = line[0:20]
        if temp != (' '*20):
            numCols = len(line[21:].split()) + 1

        # Station variance line 1
        if numCols == 11:
            stn = line[:20]
            lat = gc.hp2dec(float(line[23:36]))
            lon = gc.hp2dec(float(line[38:51]))
            hPU = float(line[51:62].strip())
            vPU = float(line[62:73].strip())
            semiMajor = float(line[73:86].strip())
            semiMinor = float(line[86:99].strip())
            orient = float(line[99:112].strip())
            xVar = float(line[112:131].strip())
            xyCoVar = float(line[131:150].strip())
            xzCoVar = float(line[150:].strip())
            continue

        # covariance block line
        elif numCols == 4:
            print(line, file=apu_typeB, end='')
            continue

        # Covariance block line.
        elif numCols == 3:
            print(line, file=apu_typeB, end='')
            continue

        # Station variance line 2
        elif numCols == 2:
            yVar = float(line[131:150].strip())
            yzCoVar = float(line[150:].strip())
            continue

        #  Station variance line 3
        elif numCols == 1:
            # zLine = line
            zVar = float(line[150:].strip())

            # form matrix, rotate to ENU if necessary, apply type Bs,
            # recalc uncertainties, rotate back, then print.
            if rotate_vcv:
                vcv_cart = np.array([[xVar, xyCoVar, xzCoVar],
                                    [xyCoVar, yVar, yzCoVar],
                                    [xzCoVar, yzCoVar, zVar]])

                vcv_local = vcv_cart2local(vcv_cart, lat, lon)

            else:
                vcv_local = np.array([[xVar, xyCoVar, xzCoVar],
                                     [xyCoVar, yVar, yzCoVar],
                                     [xzCoVar, yzCoVar, zVar]])

            # Add the Type B uncertainty
            if stn.strip() in rvsStations:
                vcv_local[0, 0] += rvsE**2
                vcv_local[1, 1] += rvsN**2
                vcv_local[2, 2] += rvsU**2
                typeB_log = typeB_log + '{:s}{:>8.4f}{:>8.4f}{:>8.4f}\n'.format(stn,rvsE,rvsN,rvsU)
            else:
                vcv_local[0, 0] += nonRvsE**2
                vcv_local[1, 1] += nonRvsN**2
                vcv_local[2, 2] += nonRvsU**2
                typeB_log = typeB_log + '{:s}{:>8.4f}{:>8.4f}{:>8.4f}\n'.format(stn,nonRvsE,nonRvsN,nonRvsU)

            # recalc uncertainty line
            ellipse = error_ellipse(vcv_local)
            a = ellipse[0]
            b = ellipse[1]
            orient = ellipse[2]
            hPU = circ_hz_pu(a, b)
            vPU = m.sqrt(vcv_local[2, 2]) * 1.96


            if rotate_vcv:
                # rotate back to XYZ
                vcv_cart = vcv_local2cart(vcv_local, lat, lon)

            # write to file
            typeB_str = '{:20}{:>16.9f}{:>15.9f}{:11.4f}{:11.4f}{:13.4f}{:13.4f}{:13.4f}'. \
                format(stn, geodepy.transform.dec2hp(lat), geodepy.transform.dec2hp(lon),
                hPU, vPU, a, b, orient)

            if rotate_vcv:
                xVar = vcv_cart[0,0]
                xyCoVar = vcv_cart[0,1]
                xzCoVar = vcv_cart[0,2]
                typeB_str = typeB_str + '{:>19.9e}{:>19.9e}{:>19.9e}\n'.format(xVar,xyCoVar,xzCoVar)
                yVar = vcv_cart[1,1]
                yzCoVar = vcv_cart[1,2]
                typeB_str = typeB_str + '{:131s}{:>19.9e}{:>19.9e}\n'.format(' '*131,yVar,yzCoVar)
                zVar = vcv_cart[2,2]
                typeB_str = typeB_str + '{:150s}{:>19.9e}'.format(' '*150,zVar)
                print(typeB_str, file=apu_typeB)
            else:
                xVar = vcv_local[0, 0]
                xyCoVar = vcv_local[0, 1]
                xzCoVar = vcv_local[0, 2]
                typeB_str = typeB_str + '{:>19.9e}{:>19.9e}{:>19.9e}\n'.format(xVar, xyCoVar, xzCoVar)
                yVar = vcv_local[1, 1]
                yzCoVar = vcv_local[1, 2]
                typeB_str = typeB_str + '{:131s}{:>19.9e}{:>19.9e}\n'.format(' ' * 131, yVar, yzCoVar)
                zVar = vcv_local[2, 2]
                typeB_str = typeB_str + '{:150s}{:>19.9e}'.format(' ' * 150, zVar)
                print(typeB_str, file=apu_typeB)

            # update dictionary for .xyz/.adj file update
            stn_unc[stn] = {'SD_E': m.sqrt(vcv_local[0,0]),
                            'SD_N': m.sqrt(vcv_local[1,1]),
                            'SD_U': m.sqrt(vcv_local[2,2])
                            }

            continue
        else:
            print(line, file=apu_typeB, end='')
    else:
        print(line, file=apu_typeB, end='')

apu_file_fh.close()
apu_typeB.close()


#---------------------------------------------------
#              read .xyz and apply type B unc.
#---------------------------------------------------

xyz_file_fh = open(xyz_file,'r')
lineCount = 0
stnLine = False
StnLineNo = 100
header = False
StnListing = False
xyz_typeB = open(xyz_file + '.TypeB','w')
headerLineCount = 0

# loop through .xyz file and apply type B StdDevs
for line in xyz_file_fh:
    lineCount += 1
    cols = line.split()
    numCols = len(cols)

    #  check for header lines. Append metadata if end of header, print if not.
    if line == '-' * 80 + '\n':
        headerLineCount += 1
        if headerLineCount == 2:
            print('Type B Uncertainties               3, 3, 6 mm for RVS '
                  'stations; 6, 6, 12 for non RVS stations. Applied by DynAdjust_TypeB.py '
                  '(version: {:s}).'.format(dateUpdated), file=xyz_typeB)
            print(line, file=xyz_typeB, end='')
            continue
        else:
            print(line, file=xyz_typeB, end='')
            continue

    # check coordinate type string is correct:
    elif line[:35] == 'Station coordinate types:          ':
        if line[35:] == 'ENzPLHhXYZ\n':
            print(line, file=xyz_typeB, end='')
        else:
            print()
            print(' Warning: Coordinate types must be ENzPLHhXY')
            print('          Exiting.')
            xyz_file_fh.close()
            xyz_typeB.close()
            log_fh.close()
            os.remove(xyz_file + '.TypeB')
            os.remove(apu_file + '.TypeB')
            os.remove('DynAdjust_TypeB.log')
            exit()

    # determine beginning of station coordinate listing
    elif line == 'Adjusted Coordinates\n':
        StnLineNo = lineCount + 5
        print(line, file=xyz_typeB, end='')
        continue
    elif lineCount >= StnLineNo:
        if line == '\n':
            print(line, file=xyz_typeB, end='')
            continue
        stn = line[:20]
        printStr = line[:158]
        try:
            StdStr = '{:12.4f}{:10.4f}{:10.4f}'.format(stn_unc[stn]['SD_E'], stn_unc[stn]['SD_N'],
                                                       stn_unc[stn]['SD_U'])
            printStr = printStr + StdStr + line[190:]
            print(printStr, file=xyz_typeB, end='')
            # print(stn, StdStr)
        except:
            warning_str = warning_str + '{:s} on line {:d} not found in {:s}\n'.format(stn.strip(), lineCount,
                                                                                       xyz_file)
        continue

    else:
        print(line, file=xyz_typeB, end='')

xyz_typeB.close()


#---------------------------------------------------
#              read .adj and apply type B unc.
#---------------------------------------------------

adj_file_fh = open(adj_file,'r')
lineCount = 0

# loop through .adj file, find if stations are listed, then and apply type B StdDevs
for line in adj_file_fh:
    lineCount += 1
    if line == 'Adjusted Coordinates\n':
        StnLineNo = lineCount + 5

adj_file_fh.close()

# if stn listing present in .adj file:
if StnLineNo > 0:
    adj_file_fh = open(adj_file, 'r')
    adj_typeB = open(adj_file + '.TypeB','w')
    lineCount = 0
    headerLineCount = 0

    for line in adj_file_fh:
        lineCount += 1

        #  check for header lines. Append metadata if end of header, print if not.
        if line == '-' * 80 + '\n':
            headerLineCount +=1
            if headerLineCount == 2:
                print('Type B Uncertainties               3, 3, 6 mm for RVS '
                      'stations; 6, 6, 12 for non RVS stations. Applied by DynAdjust_TypeB.py '
                      '(version: {:s}).'.format(dateUpdated), file=adj_typeB)
                print(line, file=adj_typeB, end='')
                continue
            else:
                print(line,file=adj_typeB, end='')
                continue
        # print line to file if before station listing, else update StdDevs.
        if lineCount < StnLineNo:
            print(line,file=adj_typeB, end='')
            continue
        else:
            if line == '\n':
                print(line, file=adj_typeB, end='')
                continue
            stn = line[:20]
            printStr = line[:158]
            try:
                StdStr = '{:12.4f}{:10.4f}{:10.4f}'.format(stn_unc[stn]['SD_E'], stn_unc[stn]['SD_N'],
                                                           stn_unc[stn]['SD_U'])
                printStr = printStr + StdStr + line[190:]
                print(printStr, file=adj_typeB,end='')
            except:
                warning_str = warning_str + '{:s} on line {:d} not found in {:s}\n'.format(stn.strip(), lineCount,
                                                                                          adj_file)
            continue

adj_file_fh.close()
adj_typeB.close()


#---------------------------------------------------
# Print program log and summary
#---------------------------------------------------

print('-'*50,file=log_fh)
print('DynAdjust_TypeB.py log file',file=log_fh)
print('-'*50,file=log_fh)
print('Program version         {:s}'.format(dateUpdated),file=log_fh)
print('Input Files:            {:s}'.format(adj_file),file=log_fh)
print('                        {:s}'.format(apu_file),file=log_fh)
print('                        {:s}'.format(xyz_file),file=log_fh)
print('-'*50,file=log_fh)
print(file=log_fh)

print('Warnings:',file=log_fh)
print('-'*50,file=log_fh)
if warning_str == '':
    print('<None>',file=log_fh)
else:
    print(warning_str,file=log_fh)
print(file=log_fh)

print('Type B uncertainties added:',file=log_fh)
print('Station                 East   North      Up',file=log_fh)
print('-'*50,file=log_fh)
print(typeB_log,file=log_fh)


log_fh.close()