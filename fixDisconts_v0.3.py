#!/usr/bin/env python

'''
This script will take a pair of DynaML files and rename any APREF stations that
have a discontinuity in their time series. Ignored measurements are left ignored
and Type G or X measurements that don't have an epoch are set to ignored.

To call:
            fixDisconts.py <root>

where <root> is the root of the input files. That is, the input files will be
<root>_stn.xml and <root>_msr.xml

The original files will be copied to *.bak and the output files will have the
same name as the input files. 

The APREF discontinuity file, apref_YYDOY.disconts needs to be in the working
directory.
'''

# Things to think about:
#   * Add logging
#   * Gaps in and APREF station's time series

from __future__ import print_function
from glob import glob
import sys, shutil, datetime

# Make backups of the two files, read in their contents, and open the output
# files
stnFile = sys.argv[1] + '_stn.xml'
msrFile = sys.argv[1] + '_msr.xml'
shutil.copyfile(stnFile, stnFile + '.bak')
shutil.copyfile(msrFile, msrFile + '.bak')
stnLines = [line.rstrip() for line in open(stnFile)]
msrLines = [line.rstrip() for line in open(msrFile)]
sf = open(stnFile, 'w')
mf = open(msrFile, 'w')

# Write the header infromation to the output files
for i in range(0, 2):
    stnHdr = stnLines[i].rstrip('\r\n')
    sf.write(stnHdr + '\n')
    msrHdr = msrLines[i].rstrip('\r\n')
    mf.write(msrHdr + '\n')

# Read in the discontinuities
disconts = {}
stnsWdiscont = set()
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

# Read the msr file into measurement blocks
msrBlocks = []
block = []
buildBlock = False
for msrLine in msrLines[2:]:
    msrLine = msrLine.rstrip('\r\n')
    if '<DnaMeasurement>' in msrLine:
        buildBlock = True
    if buildBlock:
        block.append(msrLine)
    if '</DnaMeasurement>' in msrLine:
        buildBlock = False
        msrBlocks.append(block)
        block = []

# Loop over the measurement blocks
addStn = set()
remStn = set()
ignoreString = '<Ignore>*</Ignore>'
for msrBlock in msrBlocks:
    fix = False
    epochSet = False
    for line in msrBlock:
        data = line.lstrip()
        data = data.rstrip()
        if ignoreString in data:
            for line in msrBlock:
                mf.write(line + '\n')
            break
        if 'Type' in data:
            msrType = data.replace('<Type>', '')
            msrType = msrType.replace('</Type>', '')
        if 'Epoch' in data:
            epoch = data.replace('<Epoch>', '')
            epoch = epoch.replace('</Epoch>', '')
            day = int(epoch[0:2])
            month = int(epoch[3:5])
            year = int(epoch[6:])
            try:
                date = datetime.date(year, month, day)
                doy = str(date.timetuple().tm_yday)
                yrDoy = str(year) + ('0' * (3 - len(doy)) + doy)
                epochSet = True
            except ValueError:
                pass
        if not fix:
            if 'First' in data:
                name = data.replace('<First>', '')
                name = name.replace('</First>', '')
                if name in stnsWdiscont:
                    fix = True
            if 'Second' in data:
                name = data.replace('<Second>', '')
                name = name.replace('</Second>', '')
                if name in stnsWdiscont:
                    fix = True
            if 'Target' in data:
                name = data.replace('<Target>', '')
                name = name.replace('</Target>', '')
                if name in stnsWdiscont:
                    fix = True
    if fix and epochSet:
        for line in msrBlock:
            data = line.lstrip()
            data = data.rstrip()
            if 'First' in data:
                name = data.replace('<First>', '')
                name = name.replace('</First>', '')
                if name in stnsWdiscont:
                    discnts = disconts[name][:]
                    discnts.sort()
                    discnts.reverse()
                    if yrDoy <= min(discnts):
                        discnt = min(discnts)
                        newName = name + '_' + discnt
                    else:
                        for discnt in discnts:
                            if discnt < yrDoy:
                                newName = name + '_' + discnt
                                break
                    line = line.replace(name, newName)
                    addStn.add(newName)
                    remStn.add(name)
            if 'Second' in data:
                name = data.replace('<Second>', '')
                name = name.replace('</Second>', '')
                if name in stnsWdiscont:
                    discnts = disconts[name][:]
                    discnts.sort()
                    discnts.reverse()
                    if yrDoy <= min(discnts):
                        discnt = min(discnts)
                        newName = name + '_' + discnt
                    else:
                        for discnt in discnts:
                            if discnt < yrDoy:
                                newName = name + '_' + discnt
                                break
                    line = line.replace(name, newName)
                    addStn.add(newName)
                    remStn.add(name)
            if 'Target' in data:
                name = data.replace('<Target>', '')
                name = name.replace('</Target>', '')
                if name in stnsWdiscont:
                    discnts = disconts[name][:]
                    discnts.sort()
                    discnts.reverse()
                    if yrDoy <= min(discnts):
                        discnt = min(discnts)
                        newName = name + '_' + discnt
                    else:
                        for discnt in discnts:
                            if discnt < yrDoy:
                                newName = name + '_' + discnt
                                break
                    line = line.replace(name, newName)
                    addStn.add(newName)
                    remStn.add(name)
            mf.write(line + '\n')
    elif fix and not epochSet:
        if msrType == 'G' or msrType == 'X':
            for line in msrBlock:
                line = line.replace('<Ignore/>', ignoreString)
                mf.write(line + '\n')
        else:
            yrDoy = '1991001'
            for line in msrBlock:
                data = line.lstrip()
                data = data.rstrip()
                if 'First' in data:
                    name = data.replace('<First>', '')
                    name = name.replace('</First>', '')
                    if name in stnsWdiscont:
                        discnts = disconts[name][:]
                        discnts.sort()
                        discnts.reverse()
                        if yrDoy <= min(discnts):
                            discnt = min(discnts)
                            newName = name + '_' + discnt
                        else:
                            for discnt in discnts:
                                if discnt < yrDoy:
                                    newName = name + '_' + discnt
                                    break
                        line = line.replace(name, newName)
                        addStn.add(newName)
                        remStn.add(name)
                if 'Second' in data:
                    name = data.replace('<Second>', '')
                    name = name.replace('</Second>', '')
                    if name in stnsWdiscont:
                        discnts = disconts[name][:]
                        discnts.sort()
                        discnts.reverse()
                        if yrDoy <= min(discnts):
                            discnt = min(discnts)
                            newName = name + '_' + discnt
                        else:
                            for discnt in discnts:
                                if discnt < yrDoy:
                                    newName = name + '_' + discnt
                                    break
                        line = line.replace(name, newName)
                        addStn.add(newName)
                        remStn.add(name)
                if 'Target' in data:
                    name = data.replace('<Target>', '')
                    name = name.replace('</Target>', '')
                    if name in stnsWdiscont:
                        discnts = disconts[name][:]
                        discnts.sort()
                        discnts.reverse()
                        if yrDoy <= min(discnts):
                            discnt = min(discnts)
                            newName = name + '_' + discnt
                        else:
                            for discnt in discnts:
                                if discnt < yrDoy:
                                    newName = name + '_' + discnt
                                    break
                        line = line.replace(name, newName)
                        addStn.add(newName)
                        remStn.add(name)
                mf.write(line + '\n')
    else:
        for line in msrBlock:
            mf.write(line + '\n')

# Read the stn file into station blocks
stnBlocks = []
block = []
buildBlock = False
for stnLine in stnLines[2:]:
    stnLine = stnLine.rstrip('\r\n')
    if '<DnaStation>' in stnLine:
        buildBlock = True
    if buildBlock:
        block.append(stnLine)
    if '</DnaStation>' in stnLine:
        buildBlock = False
        stnBlocks.append(block)
        block = []

# Loop over the station blocks
for stnBlock in stnBlocks:
    for line in stnBlock:
        data = line.lstrip()
        data = data.rstrip()
        if '<Name>' in data:
            name = data.replace('<Name>', '')
            name = name.replace('</Name>', '')
            break
    if name in remStn:
        for newName in addStn:
            if name in newName:
                for line in stnBlock:
#                    data = line.lstrip()
#                    data = data.rstrip()
#                    if 'XAxis' in data:
#                        x = data.replace('<XAxis>', '')
#                        x = x.replace('</XAxis>', '')
#                        line = line.replace(x, xPos[newName])
#                    if 'YAxis' in data:
#                        y = data.replace('<YAxis>', '')
#                        y = y.replace('</YAxis>', '')
#                        line = line.replace(y, yPos[newName])
#                    if 'Height' in data:
#                        z = data.replace('<Height>', '')
#                        z = z.replace('</Height>', '')
#                        line = line.replace(z, zPos[newName])
                    line = line.replace(name, newName)
#                    line = line.replace('LLH', 'XYZ')
#                    line = line.replace('LLh', 'XYZ')
#                    line = line.replace('UTM', 'XYZ')
                    sf.write(line + '\n')
    else:
        for line in stnBlock:
            sf.write(line + '\n')

sf.write('</DnaXmlFormat>\n')
mf.write('</DnaXmlFormat>\n')
sf.close()
mf.close()
