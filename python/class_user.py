#!python3
###############################################################################
# Source file : class_user.py      
# Language    : Python 3.7
# Author      : Kevin Hubbard
# Description : Example class for user defined add-on functions.
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
#
# Note: cmd_str is a text string from the command line "user1 foo" for example.
#       rts is a list of text strings that the CLI will display on completion.
# -----------------------------------------------------------------------------
# History :
#   01.01.2018 : khubbard : Created
###############################################################################
from common_functions import file2list;
from common_functions import list2file;



###############################################################################
# Example user class and methods.
#  user1 writes and reads a value from register 0x00
#  user2 reads value at register 0x04, increments it by +1 then reads again
class user:
  def __init__ ( self, lb_link ):
    self.bd = lb_link;
    # These are some constants from spi_prom.v
#   self.user_reg_00 = 0x00000000;
#   self.user_reg_04 = 0x00000004;
#   self.dram_start_addr = 0x00000004;
#   self.dram_len_dwords = 0x00000002;
    self.cmd_list= ["user1","user2","user3","dram_write","dram_read","dram_test"];
    ( self.help, self.detailed_help ) = self.init_help();


  def proc_cmd( self, cmd_txt, cmd_str ):
    if ( cmd_txt == "user1" )        : return self.user1( cmd_str );
    if ( cmd_txt == "user2" )        : return self.user2( cmd_str );
    if ( cmd_txt == "user3" )        : return self.user3( cmd_str );
    if ( cmd_txt == "dram_write" )   : return self.dram_write( cmd_str );
    if ( cmd_txt == "dram_read"  )   : return self.dram_read( cmd_str );
    if ( cmd_txt == "dram_test"  )   : return self.dram_test( cmd_str );


  def user1( self, cmd_str ):
    self.bd.wr( self.user_reg_00, [ 0x11223344 ] );
    rts = ["%08x" % ( self.bd.rd( self.user_reg_00,1 )[0] ) ];
    return rts;


  def user2( self, cmd_str ):
    rts = self.bd.rd( self.user_reg_04,1 );
    val = rts[0];
    val +=1;
    self.bd.wr( self.user_reg_04, [ val ] );
    rts = ["%08x" % ( self.bd.rd( self.user_reg_04,1 )[0] ) ];
    return rts;


  def user3( self, cmd_str ):
    rts = self.bd.rd( self.user_reg_00,2 );
    txt_rts = [ "%08x" % each for each in rts ];# list comprehension
    list2file( "bar.txt", txt_rts );
    rts = ["File bar.txt written"];
    return rts;


  def dram_write( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    if ( words[1] == None ):
      rts = [];
      rts += ["dram_write start_addr num_dwords data_dword"];
      rts += ["  start_addr : Hex start address, example 01000000"];
      rts += ["  num_dwords : Hex length in dwords, example 100"];
      rts += ["  data_dword : Hex data pattern, example 12345678"];
    else:
      start_addr = int( words[1], 16 );
      num_dwords = int( words[2], 16 );
      data_dword = int( words[3], 16 );
      data_list = [ data_dword ] * num_dwords;
      self.bd.wr( start_addr, data_list );
#     rts = [ "%08x" % each for each in data_list ];# list comprehension
      rts = [];
    return rts;


  def dram_read( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    if ( words[1] == None ):
      rts = [];
      rts += ["dram_read start_addr num_dwords filename"];
      rts += ["  start_addr : Hex start address, example 01000000"];
      rts += ["  num_dwords : Hex length in dwords, example 100"];
      rts += ["  filename   : Optional. Dump to file instead of console"];
    else:
      start_addr = int( words[1], 16 );
      num_dwords = int( words[2], 16 );
      filename   = words[3];
      hex_rts = self.bd.rd( start_addr, num_dwords );
      rts = [ "%08x" % each for each in hex_rts ];# list comprehension
      if ( filename != None ):
        list2file( filename, rts );
        rts = ["%s written" % filename ];
    return rts;


  def dram_test( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    if ( words[1] == None ):
      rts = [];
      rts += ["dram_test start_addr num_dwords data_dword read_iters filename"];
      rts += ["  start_addr : Hex start address, example 01000000"];
      rts += ["  num_dwords : Hex length in dwords, example 100"];
      rts += ["  data_dword : Hex data pattern, example 12345678"];
      rts += ["  read_iters : Optional Hex read iterations example 2"   ];
      rts += ["  filename   : Optional. Dump to file instead of console"];
    else:
      start_addr = int( words[1], 16 );
      num_dwords = int( words[2], 16 );
      data_dword = int( words[3], 16 );
      if ( words[4] == None ):
        read_iters = 1;
      else:
        read_iters = int( words[4], 16 );
      filename   = words[5];
      data_list = [ data_dword ] * num_dwords;
      self.bd.wr( start_addr, data_list );
      rts = [];
      for i in range(0,read_iters ):
        rd_list = self.bd.rd( start_addr, num_dwords );
        for ( j, rd_dword ) in enumerate( rd_list ):
          if ( rd_dword != data_list[j] ):
            addr = start_addr + 4*j;# Note DWORD to Byte Addr Translation
            rts += ["%04x %08x : %08x != %08x" % ( i, addr, rd_dword, data_list[j])];
      if ( filename != None ):
        list2file( filename, rts );
        rts = ["%s written" % filename ];
    return rts;


  def init_help( self ):
    h= [];
    dh= [];
    h+=["# DRAM Access commands                                                                 "];
    h+=["#  dram_write            : Write a pattern to DRAM                                     "];
    h+=["#  dram_read             : Read data from DRAM                                         "];
    h+=["#  dram_test             : Write then Readback a pattern to DRAM                       "];
    dh+=[("dram_write",
          "dram_write start_addr num_dwords data_dword\n"         +\
          "  start_addr : Hex start address, example 01000000\n"  +\
          "  num_dwords : Hex length in dwords, example 100\n"    +\
          "  data_dword : Hex data pattern, example 12345678\n"   )];
    dh+=[("dram_read",  
          "dram_read start_addr num_dwords filename\n"            +\
          "  start_addr : Hex start address, example 01000000\n"  +\
          "  num_dwords : Hex length in dwords, example 100\n"    +\
          "  filename   : Optional dump to file \n"               )];
    dh+=[("dram_test",
          "dram_test start_addr num_dwords data_dword read_iters filename\n" +\
          "  start_addr : Hex start address, example 01000000\n"  +\
          "  num_dwords : Hex length in dwords, example 100\n"    +\
          "  data_dword : Hex data pattern, example 12345678\n"   +\
          "  read_iters : Hex read iterations, example 2\n"       +\
          "  filename   : Optional dump to file \n"               )];
    return (h,dh);

# EOF
