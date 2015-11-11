#!/usr/bin/python

'''Utilities used by both client and server for the chat.
'''

# Imports
from __future__ import print_function

import sys

# Authorship Information
__author__     = "Joseph Cavazos"
__maintainer__ = __author__
__email__      = "Joseph.C.Cavazos@gmail.com"
__version__    = "0.1"

# Constants
DEFAULT_PORT   = 27235 
MAX_PORT       = 65535
BUFSZ          = 4096
ASCII_MIN      = 0      # (space)
ASCII_MAX      = 127    # ~
ASCII_RANGE    = ASCII_MAX - ASCII_MIN

def printErr(str):
   '''Prints string to stderr output stream.
   @param str The string to print to stderr.
   '''
   print(str, file=sys.stderr)

def printUsage(progname = __file__, docstring = __doc__):
   '''Prints the docstring/usage of the Python file.'''
   printErr(docstring % progname)

def genMaps(key):
   '''Generates encryption and decryption dictionaries based off
   Caesar cypher using the provided key.
   @param key The key used for the offset.
   @return A tuple containing the encryption and decryption dictionaries.
   '''
   baseList = [chr(char) for char in range(ASCII_MIN, ASCII_MAX + 1)]
   newList = baseList[key:] + baseList[:key]
   encMap = {k: v for k, v in zip(baseList, newList)}
   decMap = {v: k for k, v in encMap.items()}
   return (encMap, decMap)

def crypt(trans, msg):
   '''A general crypter function that translates a message
   character-by-character using the provided dictionary.
   @param trans The dictionary to use for translating the message.
   @param msg A message string that needs to be translated.
   @return The translated message.
   '''
   if trans == None:
      return msg

   if msg == None:
      return None

   return ''.join([trans[char] for char in msg])

if __name__ == '__main__':
   print("This module was not meant to be executed.")
