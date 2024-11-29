#!python3
###############################################################################
# Source file : class_lb_tcp_link.py
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
class lb_tcp_link:
# def __init__ ( self, mesa_bus, slot, subslot ):
  def __init__ ( self, ip, port ):
#   self.mesa_bus = mesa_bus;
#   self.slot      = slot;
#   self.subslot   = subslot;
    self.dbg_flag  = False;

    try:
      import socket;
    except:
      raise RuntimeError("ERROR: socket is required");
    try:
      self.sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM);
      self.sock.connect( ( ip, port ) );# "localhost", 21567
      self.sock.settimeout(5); # Dont wait forever
    except:
      self.sock = None;
      return;
  def close ( self ):
    self.sock.close();

  def set_slot(self, addr):
    payload = "mesa_slot %02x\n" % addr;
    self.tx_tcp_packet( payload );
    self.rx_tcp_packet();
    return;

  def set_subslot(self, addr):
    payload = "mesa_subslot %02x\n" % addr;
    self.tx_tcp_packet( payload );
    self.rx_tcp_packet();
    return;

  def wr_repeat(self, addr, data_list ):
    self.wr( addr, data_list, repeat = True );
    return;

  def wr(self, addr, data, repeat = False ):
    if ( repeat == False ):
      cmd = "w";# Normal Write : Single or Burst with incrementing address
    else:
      cmd = "W";# Write Multiple DWORDs to same address
    payload = "".join( [cmd + " %08x" % addr] +
                       [" %08x" % int(d) for d in data] +
                       ["\n"] );
    self.tx_tcp_packet( payload );
    self.rx_tcp_packet();
    return;

  def wr_packet(self, addr_data_list ):
    return;

  def rd( self, addr, num_dwords=1, repeat = False ):
    if ( repeat == False ):
      cmd = "r";# Normal Read : Single or Burst with incrementing address
    else:
      cmd = "k";# Read Multiple DWORDs from single address
    payload = cmd + " %08x %08x\n" % (addr,(num_dwords-1));# 0=1DWORD,1=2DWORDs
    self.tx_tcp_packet( payload );
    payload = self.rx_tcp_packet().rstrip();
    dwords = payload.split(' ');
    rts = [];
    for dword in dwords:
      rts += [int( dword, 16 )];
    return rts;

  def rd_repeat(self, addr, num_dwords ):
    rts = self.rd( addr, num_dwords, repeat = True );
    return rts;

  def tx_tcp_packet( self, payload ):
    # A Packet is a 8char hexadecimal header followed by the payload.
    # The header is the number of bytes in the payload.
    header = "%08x" % len(payload);
    bin_data = (header+payload).encode("utf-8");# String to ByteArray
    self.sock.send( bin_data );

  def rx_tcp_packet( self ):
    # Receive 1+ Packets of response. 1st Packet will start with header that
    # indicates how big the entire Backdoor payload is. Sit in a loop
    # receiving 1+ TCP packets until the entire payload is received.
    bin_data = self.sock.recv(1024);
    rts = bin_data.decode("utf-8");# ByteArray to String
    header      = rts[0:8];      # Remove the header, Example "00000004"
    payload_len = int(header,16);# The Payload Length in Bytes, Example 0x4
    payload     = rts[8:];       # Start of Payload is everything after header
    # 1st packet may not be entire payload so loop until we have it all
    while ( len(payload) < payload_len ):
      bin_data = self.sock.recv(1024);
      payload += bin_data.decode("utf-8");# ByteArray to String
    return payload;
