#!python3
###############################################################################
# Source file : class_lb_link.py
# Language    : Python 3.3 or Python 3.5
# Author      : Kevin Hubbard
# Description : 32bit Local Bus access using MesaBus       
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
#   01.01.2018 : khubbard : Created
###############################################################################



###############################################################################
# Protocol interface for MesaBus over a FTDI USB3 connection.
class lb_link:
  def __init__ ( self, mesa_bus, slot, subslot ):
    self.mesa_bus = mesa_bus;
    self.slot      = slot;
    self.subslot   = subslot;
    self.dbg_flag  = False;

  def wr_repeat(self, addr, data_list ):
    self.wr( addr, data_list, repeat = True );

  def wr(self, addr, data_list, repeat = False ):
    # LocalBus WR cycle is a Addr+Data payload
    # Mesabus has maximum payload of 255 bytes, or 63 DWORDs.
    # 1 DWORD is LB Addr, leaving 62 DWORDs available for data bursts
    # if data is more than 62 dwords, parse it down into multiple bursts
    each_addr = addr;
    if ( repeat == False ):
      mb_cmd = 0x0;# Burst Write
    else:
      mb_cmd = 0x2;# Write Repeat ( Multiple data to same address - FIFO like )

    while ( len( data_list ) > 0 ):
      if ( len( data_list ) > 62 ):
        data_payload = data_list[0:62];
        data_list    = data_list[62:];
      else:
        data_payload = data_list[0:];
        data_list    = [];
      payload = ( "%08x" % each_addr );
      for each_data in data_payload:
        payload += ( "%08x" % each_data );
        if ( repeat == False ):
          each_addr +=4;# maintain address for splitting into 62 DWORD bursts
#     print("MB.wr :" + payload );
      self.mesa_bus.wr( self.slot, self.subslot, mb_cmd, payload );
    return;

  def wr_packet(self, addr_data_list ):
    # FT600 has a 1024 byte limit. My 8bit interface halves that to 512 bytes
    # and send ASCII instead of binary, so 256
    max_packet_len = 30;
    while ( len( addr_data_list ) > 0 ):
      if ( len( addr_data_list ) > max_packet_len ):
        data_payload   = addr_data_list[0:max_packet_len];
        addr_data_list = addr_data_list[max_packet_len:];
      else:
        data_payload   = addr_data_list[0:];
        addr_data_list = [];
      payload = "";
      for each_data in data_payload:
        payload += ( "%08x" % each_data );
      mb_cmd = 0x4;# Write Packet
#     print("MB.wr :" + payload );
      self.mesa_bus.wr( self.slot, self.subslot, mb_cmd, payload );
    return;

  def rd_repeat(self, addr, num_dwords ):
    rts = self.rd( addr = addr, num_dwords=num_dwords , repeat = True );
    return rts;

  def rd(self, addr, num_dwords, repeat = False ):
    max_payload = 31;
    if ( num_dwords <= max_payload ):
      rts = self.rd_raw( addr, num_dwords, repeat );
    else:
      # MesaBus has 63 DWORD payload limit, so split up into multiple reads
      dwords_remaining = num_dwords;
      rts = [];
      while( dwords_remaining > 0 ):
        if ( dwords_remaining <= max_payload ):
          rts += self.rd_raw( addr, dwords_remaining, repeat );
          dwords_remaining = 0;
        else:
          rts += self.rd_raw( addr, max_payload, repeat );
          dwords_remaining -= max_payload;
          if ( repeat == False ):
            addr += max_payload*4;# Note Byte Addressing
    return rts;

  def rd_raw(self, addr, num_dwords, repeat = False ):
    dwords_remaining = num_dwords;
    each_addr = addr;
    if ( repeat == False ):
      mb_cmd = 0x1;# Normal Read
    else:
      mb_cmd = 0x3;# Read  Repeat ( Multiple data to same address )

    # LocalBus RD cycle is a Addr+Len 8byte payload to 0x00,0x0,0x1
    payload = ( "%08x" % each_addr ) + ( "%08x" % num_dwords );
#   print("MB.wr :" + payload );
    self.mesa_bus.wr( self.slot, self.subslot, mb_cmd, payload );
    rts_str = self.mesa_bus.rd( num_dwords = num_dwords );
#   print("MB.rd :" + rts_str );

    rts = [];
    if ( len( rts_str ) >= 8 ):
      while ( len( rts_str ) >= 8 ):
        rts_dword = rts_str[0:8];
        rts_str   = rts_str[8:];
        try:
          rts += [ int( rts_dword, 16 ) ];
        except:
          addr_str = "%08x" % each_addr;
          print("ERROR: Invalid LocalBus Read >" +
                 addr_str + "< >" + rts_mesa + "< >" + rts_dword + "<");
          if ( self.dbg_flag == "debug" ):
            sys.exit();
          rts += [ 0xdeadbeef ];
    else:
      print("ERROR: Invalid LocalBus Read >" + rts_str + "<");
      rts += [ 0xdeadbeef ];
    return rts;
