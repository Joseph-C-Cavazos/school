#!/usr/bin/python

# Docstring for script. Auto-assigned to __doc__
'''Usage: %s [-o outfile] [-d [timer]] [-x excludeFile] [-r rootDir] [-h | --help]
   DESCRIPTION
      A program that will run

   OPTIONS
      -o outfile: Will use the file outfile to store the results of the scan. If the file is already properly populated before running, it will be used for comparison of file hashes. If a file is specified and being compared against, the new data will overwrite the old and any changes printed to STDOUT. If no file is specified, the raw data will be printed to STDOUT. This file will automatically be excluded from being scanned.

      -d [timer]: Will start the program as a daemon that will periodically rerun every [timer] number of seconds after the completion of the previous scan. If no timer is specified, it will default to a built-in 1 minute.
      NOTE: This is the time from when the previous run ends to when the new one will begin. Meaning that the actual processing of files will not begin until [timer] seconds after the previous run has finished.

      -x excludeFile: This specifies a file, excludeFile, that will be read in as a list of files and directories to be excluded from the scan.

      -r rootDir: This specifies the root directory from which the scan will begin. If no directory is specified the current/present working directory will be used.

      -h | --help: Will show this usage message.
'''

# Imports
## Imported print_function from __future__ to permit "proper" stderr printing.
from __future__ import print_function
import sys, os, pickle, traceback, hashlib, time, stat

# Authorship Information
__author__ = "Joseph Cavazos"
__maintainer__ = __author__
__email__ = "Joseph.C.Cavazos@gmail.com"
__version__ = "0.1"

# Constants
TIMER_DEFAULT = 60   # Default number of seconds for timer.
FILL_WIDTH = 50      # Number of times to repeat the string on breaks.
FILE_BUF = 4096      # Number of bytes to read into the buffer at a time.

# Utility/Helper Functions
def printErr(str):
   '''Prints string to stderr output stream.
   @param str The string to print to stderr.
   '''
   print(str, file=sys.stderr)

def printHashes(hashes, keys=None):
   '''Prints the hashes contained in a dictionray in the format:
   "[hash] - path".
   @param hashes The dictionary of hashes and paths.
   @param keys The list of keys. If not defined, the keys from
      hashes will be used.
   '''
   if not keys is None:
      tmpKeys = keys
   else:
      tmpKeys = hashes

   for key in tmpKeys:
      print("[%s] - %s" % (hashes[key], key))

def lineBreak(pre='', post='', fill='-', mult=FILL_WIDTH):
   '''Prints a visual separation to stdout by repeating a string multiple times.
   @param pre The string to print before the break. Defaults to ''.
   @param post The string to print after the break. Defaults to ''.
   @param fill The string used as the separator. Defaults to '-'.
   @param mult The number of times to repeat the fill string. Defaults to FILL_WIDTH.
   '''
   print("%s%s%s" % (pre, fill * mult, post))

# NOTE: This function is an exact copy from StackOverflow Question #3431825
# Unfortunately, due to large files exceeding memory contraints, the need
# for buffering came into effect and I was unsure how to do it in terms of
# Python.
def md5sum(filename):
   '''Returns an md5 hash of the contents of a file.
   @param filename The file to be opened and hashed.
   @return The md5 hash of the contents of the file.
   '''
   hash = hashlib.md5()
   with open(filename) as f:
      for chunk in iter(lambda: f.read(FILE_BUF), ""):
         hash.update(chunk)
   return hash.hexdigest()

# Primary Functions
def printUsage():
   '''Prints the docstring/usage of the Python script file.'''
   printErr(__doc__ % __file__)

def parseArgs(args):
   '''Parses through an argument list to return a dictionary matching the options to key-value pairs.
   @param args The argument list to parse through.
   @return A dictionary containing definitions according to options passed to the script.
   '''
   # Strips out the base program name so as not to be read in through loop.
   argHash = {'progname':args.pop(0)}
   
   # Loop to take off first argument through progression
   while len(args) > 0:
      arg = args.pop(0)

      # Help / Usage option
      if arg == '-h' or arg == '--help':
         printUsage()
         sys.exit(1)

      # Root Directory option
      elif arg == '-r':
         if len(args) == 0:
            printErr("ERROR: -r expects root directory path to follow option")
            sys.exit(1)
         argHash['rootDir'] = args.pop(0)

      # Exclude File option
      elif arg == '-x':
         if len(args) == 0:
            printErr("ERROR: -x expects a file containing excluded paths to follow option")
            sys.exit(1)
         argHash['exFilename'] = args.pop(0)

      # "Daemon" Mode option
      elif arg == '-d':
         argHash['daemon'] = True
         if len(args) > 0:
            if not args[0].startswith('-'):
               argHash['timer'] = args.pop(0)

      # Output File option
      elif arg == '-o':
         if len(args) == 0:
            printErr("ERROR: -o expects a filename for the output file to follow option")
            sys.exit(1)
         argHash['outFilename'] = args.pop(0)

      # Unknown option
      else:
         printErr("ERROR: Unrecognized option. Please run with the -h option to display help and usage")
         sys.exit(1)

   return argHash

def checkOpts(args):
   '''Performs rigorous checking of arguments successfully parsed to determine they are formatted correctly.
   @param args The formatted dictionary of arguments received by the script.
   @return A dictionary correctly formatted for use in the remainder of the script.
   '''
   # Checks if the root directory exists and exists within the filesystem.
   if not 'rootDir' in args:
      args['rootDir'] = os.getcwd()
   else:
      tmpRoot = os.path.abspath(args['rootDir'])
      if not os.path.isdir(tmpRoot):
         printErr("ERROR: Unable to find path for root directory: %s\n" % (args['rootDir']))
         sys.exit(1)
      args['rootDir'] = tmpRoot

   # Checks if the exclude filename exists and attempts to open it for reading.
   if 'exFilename' in args:
      try:
         args['exFile'] = open(args['exFilename'], 'r')
      except IOError as ex:
         printErr("ERROR: Unable to open file: %s\n%s" % (args['exFilename'], ex.strerror))
         sys.exit(1)

   # Checks if the output filename exists and attempts to open it for reading/writing.
   if 'outFilename' in args:
      try:
         args['outFile'] = open(args['outFilename'], 'ab+')
      except IOError as ex:
         printErr("ERROR: Unable to open file: %s\n%s" % (args['outFilename'], ex.strerror))
         sys.exit(1)

   # Assigns daemon boolean. 1/2 redundant.
   args['daemon'] = 'daemon' in args

   # Checks if timer has been defined. If yes, set timer to newly specified timer. If not, use default timer.
   if 'timer' in args:
      if not args['timer'].isdigit():
         printErr("ERROR: Timer is expected to be the number of seconds between scans")
         sys.exit(1)
      args['timer'] = float(args['timer'])
   else:
      args['timer'] = float(TIMER_DEFAULT)

   return args

# "Main"
# Parses incoming arguments into dictionary.
args = parseArgs(sys.argv)
# Checks arguments for formatting and refines dictionary to "expected" values.
args = checkOpts(args)
oldHashes = None

# Will load previous hashes if they exist.
if 'outFilename' in args:
   # Opening with "a+" mode worked to permit creating the file if it didn't exist
   # as well as permitting the file to be read before being overwritten. The
   # caveat is that it seeks to the end of the file, requiring a seek to the start
   # of the file.
   args['outFile'].seek(0)

   # Load serialized dictionary into oldHashes variable.
   try:
      oldHashes = pickle.load(args['outFile'])
   except EOFError as ex:
      printErr("WARNING: Output file is empty. Will be treated as empty and overwritten: %s" % (args['outFile'].name))
   except Exception as ex:
      printErr("ERROR: Output file not formatted correctly: %s\nERROR: To prevent harming file, program will terminate.\n%s" % (args['outFile'].name, ex))
      traceback.print_tb(sys.exc_info()[2])
      sys.exit(1)

# Will format exclude file contents into absolute paths for directories and filenames.
if 'exFile' in args:
   exList = args['exFile'].read().splitlines()
   exList = [os.path.abspath(path) for path in exList]
   args['exFile'].close()
else:
   exList = ()

# Primary Loop
while True:
   hashes = dict()

   # Directory walking. Setting topdown to True and the following line permits
   # os.walk() to be able to ignore directories if their names are found in the
   # exclude list.
   for rootDir, dirs, filenames in os.walk(args['rootDir'], topdown=True):
      dirs[:] = [d for d in dirs if os.path.join(rootDir, d) not in exList]
      # Walk files present in directory.
      for filename in filenames:
         absPath = os.path.join(rootDir, filename)
         # File will be skipped if found in the exlude list.
         if absPath in exList:
            continue

         # Files that do not exist are skipped.
         if not os.path.exists(absPath):
            continue

         # Files that are not "regular" (e.g. special block devices, etc.) are skipped.
         mode = os.stat(absPath).st_mode
         if not stat.S_ISREG(mode):
            printErr("Skipping non-regular file: %s" % (absPath))
            continue

         # Attempt to md5sum a file. Will fail if file cannot be opened for reading (commonly file permissions).
         try:
            #md5 = hashlib.md5(open(absPath, 'rb').read()).hexdigest()
            md5 = md5sum(absPath)
            hashes[absPath] = md5
         except IOError as ex:
            printErr("ERROR: Opening file: %s\n%s\nSkipping file to continue" % (absPath, ex.strerror))
            continue

   # Formatted output of results. Uses date as a header for block.
   lineBreak("Check Completed: %s\n" % (time.ctime()), '', '~', FILL_WIDTH + 10)

   # If an output file is open, dump dictionary of hashes to it.
   if 'outFile' in args:
      args['outFile'].seek(0)
      args['outFile'].truncate()
      pickle.dump(hashes, args['outFile'])
      print("Hashes dumped to output file: %s" % (args['outFile'].name))

   # If prior hashes don't exist, print unique header, then dump hashes and paths
   # to stdout.
   if oldHashes is None:
      lineBreak("Initial Scan\n")
      printHashes(hashes)
   else:
      # Find added, deleted, and differing hashes between hashes and oldHashes.
      added = list(set(hashes.keys()) - set(oldHashes.keys()))
      deleted = list(set(oldHashes.keys()) - set(hashes.keys()))
      changed = list(k for k in hashes.keys() if k in oldHashes.keys() and not hashes[k] == oldHashes[k])

      # Formatted output for comparing old and new hashes.
      lineBreak("Prior Hashes Found, Comparing\n")
      print("Files Newly Accesible (Likely Created):")
      printHashes(hashes, added)
      lineBreak()
      print("Files Altered:")
      printHashes(hashes, changed)
      lineBreak()
      print("Files Newly Inaccesible (Likely Deleted) [Prior Hashes]:")
      printHashes(oldHashes, deleted)

   # Current hashes will be compared to for next iteration.
   oldHashes = hashes
   lineBreak('','\n','~',FILL_WIDTH + 10)

   # Not running in "daemon" mode will break from the loop.
   if not args['daemon']:
      break

   # Sleep based on timer.
   time.sleep(args['timer'])
