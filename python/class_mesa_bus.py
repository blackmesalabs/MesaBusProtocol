#!python3
###############################################################################
# Source file : class_mesa_bus.py
# Language    : Python 3.3 or Python 3.5
# Author      : Kevin Hubbard
# Description : Access hardware over MesaBus
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
# Routines for Reading and Writing Payloads over MesaBus
# A payload is a series of bytes in hexadecimal string format. A typical use
# for MesaBus is to transport a higher level Local Bus protocol for 32bit
# writes and reads. MesaBus is lower level and transports payloads to a
# specific device on a serial chained bus based on the Slot Number.
# More info at : https://blackmesalabs.wordpress.com/2016/03/04/mesa-bus/
#  0x0 : Write Cycle    : Payload of <ADDR><DATA>...
#  0x1 : Read  Cycle    : Payload of <ADDR><Length> 
#  0x2 : Write Repeat   : Write burst data to single address : <ADDR><DATA>...
#  0x3 : Read  Repeat   : Read burst data from single address : <ADDR><Length> 
#  0x4 : Write Multiple : Payload of <ADDR><DATA><ADDR><DATA><ADDR><DATA>..
class mesa_bus:
  def __init__ ( self, phy_link ):
    self.phy_link = phy_link;
#   if ( type( phy_link ) == uart_usb_link ):
#     self.lf = "\n";
#   else:
#     self.lf = "";
    self.lf = "\n";
#   self.phy_link.wr( self.lf );# 
    self.phy_link.wr( 256*"FF" + self.lf );# 


  def wr( self, slot, subslot, cmd, payload ):
    preamble  = "FFF0";# Establish nibble-byte ordering "F0" is 1st Byte
    slot      = "%02x" % slot;
    subslot   = "%01x" % subslot;
    cmd       = "%01x" % cmd;
    num_bytes = "%02x" % int( len( payload ) / 2 );
    mesa_str  = preamble + slot + subslot + cmd + num_bytes + payload + self.lf;
    self.phy_link.wr( mesa_str );
    return;

  def rd( self, num_dwords ):
    #   "F0FE0004"+"12345678"
    #   "04" is num payload bytes and "12345678" is the read payload
    rts = self.phy_link.rd( bytes_to_read = (1+num_dwords)*4 );
    if ( len( rts ) > 8 ):
      rts = rts[8:];# Strip the "FOFE0004" header
    return rts;
