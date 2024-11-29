#!python3
###############################################################################
# Source file : common_functions.py
# Language    : Python 3.3 or Python 3.5
# Author      : Kevin Hubbard
# Description : Commonly used functions   
# License     : GPLv3
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation, either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program.  If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------
# History :
#   08.28.2018 : khubbard : Created
###############################################################################
# Example for referencing from other file:
#   from common_functions import file2list;
#   from common_functions import list2file;


def list2file( file_name, my_list, concat = False ):
  if ( concat ):
    type = 'a';
  else:
    type = 'w';

  file_out  = open( file_name, type );
  for each in my_list:
    file_out.write( each + "\n" );
  file_out.close();
  return;


def file2list( file_name, binary = False ):
  if ( binary == False ):
    file_in   = open ( file_name, 'r' );
    file_list = file_in.readlines();
    file_list = [ each.strip('\n') for each in file_list ];# list comprehension
    return file_list;
  else:
    # See https://stackoverflow.com/questions/1035340/
    #           reading-binary-file-and-looping-over-each-byte
    byte_list = [];
    file_in = open ( file_name, 'rb' );
    try:
      byte = file_in.read(1);
      while ( byte ):
        byte_list += [ord(byte)];
        byte = file_in.read(1);
    finally:
      file_in.close();
    return byte_list;


###############################################################################
# Given a file_header ( like foo_ ), check for foo_0000, then foo_0001, etc
# and return 1st available name.
def make_unique_filename( self, file_header, file_ext ):
  import os;
  num = 0;
  while ( True ):
    file_name = file_header + ( "%04d" % num ) + file_ext;
    if ( os.path.exists( file_name ) == False ):
      return file_name;
    else:
      num +=1;
  return None;
