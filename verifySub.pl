#!/usr/bin/env perl

# NAME:
#     verifySub.pl
# PURPOSE:
#     To verfiy that the RINEX files in a submission folder are suitable for
#     submission
# EXPLANATION:
#     The script is run from inside the submission folder. It runs the 
#     following checks:
# 
#i        0) File name length; 
#         1) An entry in RinexAntLs.txt;
#         2) RINEX compliance;
#         3) RINEX version (cannot process version 3.0, yet);
#         4) Observation length (greater than 6 hrs but less than 48 hrs); 
#         5) Sample interval (should be 30 seconds);
#         6) Antenna type is supported;
#         7) The file is from 1 June, 1994 or later (no IGS products before
#            that time; and
#         8) DOY, i.e., that the DOY in the filename matches the first DOY
#            of the data
#
#     Files that fail any of the first eight checks are moved to a
#     sub-directory determined by what test it failed, 'noEntry', 'nonComp',
#     'version3', 'tooShort', 'tooLong', 'sample', 'antenna', or 'date'. In
#     all eight cases these failed files can be deleted immediately by invoking
#     the '-d' switch.
#
#     Files that fail the last check can either be moved to a sub-directory
#     'wrongDOY' or immediately renamed by invoking the -r switch.
#
#     Entries in RinexAntLs.txt that do not have a corresponding RINEX file
#     are removed.
#
#     The log file also records all the files that failed each check.
# USAGE:
#     verifySub.pl -dr
#     verifySub.pl -h displays the help information
#     verifySub.pl -v displays the version information
# INPUT:
#     There is no input
# OUTPUT:
#     A log file listing all the files that failed each of the checks. Depending
#     on the usage the directory structure and contents are modified

$version = '0.13';

# HISTORY:
#     0.01    2014-08-08  Craig Harrison
#         - Inital version
#     0.02    2014-08-12  Craig Harrison
#         - Added the correct DOY to the log file for those files found to have
#             the incorrect DOY
#     0.03    2014-08-27  Craig Harrison
#         - Added RINEX version 3.0 check
#     0.04    2015-01-14  Craig Harrison
#         - Replaced the UNIX command 'head' with a line read
#     0.05    2015-01-30  Craig Harrison
#         - Removed the code that deletes exisitng directories, such as
#             tooLong or wrongDOY, which can cause inexperienced users to
#             inadvertantly delete their data
#     0.06    2015-03-10  Craig Harrison
#         - Added a sample interval check; must be 30 seconds 
#     0.07    2015-03-24  Craig Harrison
#         - Added code to account for the teqc date problem
#         - Added a RinexAntLs.txt check
#         - Changed minimum time to 05:59:00 for technical reasons
#         - Other small improvements
#     0.08    2015-08-13  Craig Harrison
#         - Added an antenna type check
#         - Added date check, there are no IGS products before 1 June, 1994
#     0.09    2015-09-03  Craig Harrison
#         - Minor bug fixes
#     0.10    2015-10-15  Craig Harrison
#         - Windows support removed
#         - More information provided when terminating to prevent files being
#             over-written
#     0.11    2016-03-16  Craig Harrison
#         - Modified to allow for pre-defined clusters
#         - Added filename length check
#     0.12    2016-05-25  Craig Harrison
#         - Modified to account for the new NGCA achive procedures
#         - Removed the clusters functionality
#     0.13    2018-02-22  Craig Harrison
#         - Implemented an antenna height check using 'looks_like_number'
#
# Load the necessary modules
use File::Copy;
use DateTime::Precise;
use Scalar::Util qw(looks_like_number);

# Parse the command line
if ($ARGV[0] eq '-h') {
    &helpInfo;
} elsif ($ARGV[0] eq '-v') {
    &versionInfo;
} elsif ($ARGV[0] eq '-dr' or $ARGV[0] eq '-rd') {
    $delete = $rename = 1;
} elsif ($ARGV[0] eq '-d') {
    $delete = 1;
} elsif ($ARGV[0] eq '-r') {
    $rename = 1;
} elsif ($ARGV[0] eq '') {
    $delete = $rename = 0;
} else {
    print "\n### UNKNOWN COMMAND LINE SWITCH ###\n";
    &helpInfo;
}

# Open the log file
open LOG, '>verifySub.log';

# Set some variables
$tooShort = 21540; # 05:59:00 hours in seconds
$tooLong = 172800; # 48 hours in seconds

# Read in the supported antenna types
&ants;
for $antType (@antTypes) {$supportedAnt{$antType}++}

# Create variables that will hold the names of files that failed the various
# tests
$failedCheck0 = $failedCheck1 = $failedCheck2 = $failedCheck3 = $failedCheck4a
    = $failedCheck4b = $failedCheck5 = $failedCheck6 = $failedCheck7
    = $failedCheck8 = '';
@failedCheck7 = ();

# Check the file name lengths
for $file (glob'*.??[oO]') {
    if (length $file ne 12) {
        if ($delete) {
            unlink $file;
        } else {
            mkdir 'badName' unless (-d 'badName');
            move $file, badName;
        }
        $failedCheck0 .= "$file\n";
        $ucFile = uc $file;
        $deleted{$ucFile}++;
    }
}    

# Check that each RINEX file has an entry in RinexAntLs.txt
# Capitalize the file names and their entries in RinexAntLs.txt
# Check the antenna type is supported
open IN, 'RinexAntLs.txt' || die "Can't find RinexAntLs.txt\n";
while (<IN>) {
    unless (/^$/ or /^\s+$/) {
        $line = $_;
        @_ = split ' ', $_;
        die "$_[0]: antenna heights must be a number\n" unless looks_like_number($_[2]); 
        $ucFile = uc $_[0];
        $line =~ s/$_[0]/$ucFile/ unless ($ucFile eq $_[0]);
        $line{$ucFile} = $line;
        unless ($supportedAnt{$_[1]}) {
            push @failedCheck7, $ucFile;
            $failedCheck7 .= "$ucFile\n";
        }
    }
}    

open OUT, '>RinexAntLs.txt';
open OUT1, '>nameChanges.ver';
for $file (glob'*.??[oO]') {
    if ($file ne uc $file) {
        if (-e uc $file) {
                $newFile = uc $file;
                print "$file can't be capitalized to $newFile: ";
                print "$newFile already exists\n";
                die "Program terminated\n";
        }
    }        
    $ucFile = uc $file;
    if ($line{$ucFile}) {
        unless ($ucFile eq $file) {
            move $file, $ucFile;
            print OUT1 "$ucFile $file\n";
        }    
        print OUT $line{$ucFile};
        $seen{$ucFile}++;
    } else {
        if ($delete) {
            unlink $file;
        } else {    
            mkdir 'noEntry' unless (-d 'noEntry');
            move $file, noEntry;
        }    
        $failedCheck1 .= "$file\n";
    }
}    
close OUT;
close OUT1;

# Deal with files that have an unsupported antenna type
for $file (@failedCheck7) {
    if ($delete) {
        unlink $file;
    } else {
        mkdir 'antenna' unless (-d 'antenna');
        move $file, antenna;
    }
    $ucFile = uc $file;
    $deleted{$ucFile}++;
}

# Check that the RINEX file begins after 1 June, 1994, i.e., DOY 152 in 1994
for $file (glob'*.??O') {
    @output = `teqc +meta +doy +quiet $file`;
    if (@output) {
        @_ = grep /start date/, @output;
        @_ = split ' ', $_[0];
        $year = (split ':', $_[4])[0];
        $doy = (split ':', $_[4])[1];
        if ($year < 1994) {
            $fileCheck8 .= $file;
            if ($delete) {
                unlink $file;
            } else {
                mkdir 'date' unless (-d 'date');
                move $file, date;
            }
            $ucFile = uc $file;
            $deleted{$ucFile}++;
        }
        if ($year eq 1994 && $doy < 152) {
            $fileCheck8 .= $file;
            if ($delete) {
                unlink $file;
            } else {
                mkdir 'date' unless (-d 'date');
                move $file, date;
            }
            $ucFile = uc $file;
            $deleted{$ucFile}++;
        }
    }
}

# Check for the teqc date problem
for $file (glob'*.??O') {
    open TMP, '>tmp';
    `teqc +meta +quiet $file 2> tmp`;
    close TMP;
    open TMP, 'tmp';
    $_ = <TMP>;
    if (/unknown RINEX date format/) {
        $dateProb{$file}++;
    }    
}
print LOG "### Unknown RINEX date format removed ###\n" if ($dateProb); 
$string = " " x 60;
$string .= "PGM / RUN BY / DATE\n";
for $key (keys %dateProb) {
    print LOG "$key\n";
    move $key, tmp;
    open IN, 'tmp';
    open OUT, ">$key";
    $_ = <IN>;
    print OUT $_;
    print OUT $string;
    <IN>;
    while (<IN>) {print OUT $_}
}    
unlink 'tmp';

# Loop over all the RINEX files
for $file (glob'*.??O') {

# Check for RINEX version 3 files
    open IN, $file;
    $ver = (split' ', <IN>)[0];
    close IN; 
    if ($ver eq '3.00') {
        $failedCheck3 .= "$file\n";

# Depending on the switches either move the file or delete it
        if ($delete) {
            unlink $file;
        } else {    
            mkdir 'version3' unless (-d 'version3');
            move $file, version3;
        }    
        $ucFile = uc $file;
        $deleted{$ucFile}++;
        next;
    }

# Run teqc
    $err = $file . '.err';
    @output = `teqc +meta +quiet +err $err $file`;

# If the RINEX file is compliant
    if (@output) {

# Check the observation length
        $length = &getLength(@output);

# If the length is too short        
        if ($length < $tooShort) {
            $length = sprintf '%d', $length;
            $failedCheck4a .= "$file ($length)\n";

# Depending on the switches either move the file or delete it
            if ($delete) {
                unlink  $file;
            } else {
                mkdir 'tooShort' unless (-d 'tooShort');
                move $file, tooShort;
            }
            $ucFile = uc $file;
            $deleted{$ucFile}++;
            next;
        }
        
# If the length is too long        
        if ($length > $tooLong) {
            $length = sprintf '%d', $length;
            $failedCheck4b .= "$file ($length)\n";

# Depending on the switches either move the file or delete it
            if ($delete) {
                unlink $file;
            } else {
                mkdir 'tooLong' unless (-d 'tooLong');
                move $file, tooLong;
            }    
            $ucFile = uc $file;
            $deleted{$ucFile}++;
            next;
        }

# Run teqc again to perform the sample interval and DOY check
        @output = `teqc +meta +doy +quiet $file`;

# Sample interval check
        $sample = &getSample(@output);
        if ($sample != 30) {
            $failedCheck5 .= "$file ($sample)\n";

# Depending on the switches either move the file or delete it
            if ($delete) {
                unlink $file;
            } else {
                mkdir 'sample' unless (-d 'sample');
                move $file, sample;
            }    
            $ucFile = uc $file;
            $deleted{$ucFile}++;
            next;
        }
            
# DOY check
        $doy1 = substr $file, 4, 3;
        $doy2 = &getDOY(@output);
        ($newFile = $file) =~ s/$doy1/$doy2/;
        if ($doy1 != $doy2) {
            $failedCheck6 .= "$file -> $newFile\n";
            
# Depending on the switches either move the file or rename it
            if ($rename) {
                if (-e $newFile) {
                    print "$file can't be renamed $newFile: i";
                    print "file already exists\n";
                    die "Program terminated\n";
                }    
                move $file, $newFile;
                $doyFixed{$file} = $newFile;
            } else {
                mkdir 'wrongDOY' unless (-d 'wrongDOY');
                move $file, wrongDOY;
                $ucFile = uc $file;
                $deleted{$ucFile}++;
            }
        }

# If there is no output then the RINEX file is non-compliant, so move it to the
# sub-directory 'nonComp'
    } else {
        $failedCheck2 .= "$file\n";
        mkdir 'nonComp' unless (-d 'nonComp');
        move $file, nonComp;
        move $err, nonComp;
        $ucFile = uc $file;
        $deleted{$ucFile}++;
    }    
}

# Update RinexAntLs.txt
`mv RinexAntLs.txt tmp`;
open OUT, '>RinexAntLs.txt';
open TMP, 'tmp';
while (<TMP>) {
    $line = $_;
    split;
    unless ($deleted{$_[0]}) {
        $line =~ s/$_[0]/$doyFixed{$_[0]}/ if ($doyFixed{$_[0]});
        print OUT $line;
    }    
}
close OUT;
unlink 'tmp';

# Write files that failed any of the checks to the log file
if ($failedCheck0) {
    print LOG "### Bad file name ###\n";
    print LOG $failedCheck0;
}    
#if ($failedCheck1a) {
#    print LOG "### No entry in RinexAntLs.txt ###\n";
#    print LOG $failedCheck1a;
#} 
#if ($failedCheck1b) {
#    print LOG "### No RINEX file ###\n";
#    print LOG $failedCheck1b;
#}
if ($failedCheck1) {
    print LOG "### No entry in RinexAntLs.txt ###\n";
    print LOG $failedCheck1;
} 
if ($failedCheck2) {
    print LOG "### Non-compliant RINEX files ###\n";
    print LOG $failedCheck2;
}    
if ($failedCheck3) {
    print LOG "### RINEX version 3 files ###\n";
    print LOG $failedCheck3;
}    
if ($failedCheck4a) {
    print LOG "### Too short (<$tooShort) ###\n";
    print LOG $failedCheck4a;
}    
if ($failedCheck4b) {
    print LOG "### Too long (>$tooLong) ###\n";
    print LOG $failedCheck4b;
}    
if ($failedCheck5) {
    print LOG "### Incorrect sampling interval ###\n";
    print LOG $failedCheck5;
}
if ($failedCheck6) {
    print LOG "### Incorrect DOY ###\n";
    print LOG $failedCheck6;
}
if ($failedCheck7) {
    print LOG "### Unsupported antenna type ###\n";
    print LOG $failedCheck7;
}
if ($failedCheck8) {
    print LOG "### File acquired too early ###\n";
    print LOG $failedCheck8;
}

# Print to screen the number of RINEX files and the number of stations
%seen = ();
for $file (glob'*.??O') {
    $num1++;
    $station = lc(substr $file, 0, 4);
    $seen{$station}++;
}
$num2 = keys %seen;
if ($num1) {
    print "There are $num1 RINEX files and $num2 stations\n";
} else {
    print "No file passed any of the tests\n";
}

# Remove the empty error files
unlink glob'*.err';

# Remove namesChanges.ver if empty
unlink 'nameChanges.ver' if (-z 'nameChanges.ver');

###############################################################################
# This sub-routine prints the help information
sub helpInfo {
    $prog = (split '/', $0)[-1];
    print "\nUsage:\n\n";
    print "$prog -dr -v -h\n\n";
    print "\t-d\tDelete files that fail the observation length, version, or\n";
    print "\t\t  sample interval check. The default is to move the files to a";
    print "\n\t\t  sub-directory.\n\n";
    print "\t-r\tRename files that fail the DOY check. The default is to\n";
    print "\t\t  move the files to a sub-directory.\n\n";
    print "The above two switches can be combined into one, ";
    print "i.e., -dr or -rd\n\n";
    print "\t-h\tPrint this help information\n";
    print "\t-v\tPrint the version information\n";
    die "\n";
}    
###############################################################################
# This sub-routine prints the version information
sub versionInfo {
    $prog = (split '/', $0)[-1];
    print "\n";
    print "$prog v$version\n";
    die "\n";
}
###############################################################################
# This sub-routine calculates the observation length
sub getLength {
    my @output = @_;
    @_ = grep /start date/, @output;
    @_ = split ' ', $_[0];
    $_ = "$_[4] $_[5]";
    my $start = DateTime::Precise->new($_);
    my $offset = $start->gps_seconds_since_epoch;
    @_ = grep /final date/, @output;
    @_ = split ' ', $_[0];
    $_ = "$_[4] $_[5]";
    my $final = DateTime::Precise->new($_);
    my $duration = $final - $start;
    return $duration;
}
###############################################################################
# This sub-routine gets the first DOY of observation
sub getDOY {
    my @output = @_;
    @_ = grep /start date/, @output;
    @_ = split ' ', $_[0];
    my $doy = (split ':', $_[4])[1];
    return $doy
}
###############################################################################
# This sub-routine gets the sample interval
sub getSample {
    my @output = @_;
    @_ = grep /sample interval/, @output;
    my $sample = (split ' ', $_[0])[2];
    return $sample
}
###############################################################################
#
#
sub ants {
    open IN,'/nas/users/u74392/unix/antTypes.dat';
    while (<IN>) {
        split;
        $antType{$_[0]}++;
    }
    for $key (keys %antType) {
        push @antTypes, $key
    }        
}
