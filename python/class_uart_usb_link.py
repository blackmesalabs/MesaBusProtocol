#!python3
###############################################################################
# Source file : class_uart_usb_link.py
# Language    : Python 3.3 or Python 3.5
# Author      : Kevin Hubbard
# Description : Access to HW via FT232 like standard serial port
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
# Serial port class for sending and receiving ASCII strings to FT232RL UART
class uart_usb_link(object):
  def __init__ ( self, port_name, baudrate ):
    try:
      import serial;
    except:
      raise RuntimeError("ERROR: PySerial from sourceforge.net is required");
      raise RuntimeError(
         "ERROR: Unable to import serial\n"+
         "PySerial from sourceforge.net is required for Serial Port access.");
    try:
      self.ser = serial.Serial( port=port_name, baudrate=baudrate,
                               bytesize=8, parity='N', stopbits=1,
                               timeout=1, xonxoff=0, rtscts=0,dsrdtr=0);
      self.port = port_name;
      self.baud = baudrate;
      self.ser.flushOutput();
      self.ser.flushInput();
      self.ack_state = True;
    except:
      raise RuntimeError("ERROR: Unable to open USB COM Port "+port_name)

  def rd( self, bytes_to_read ):
    rts = self.ser.readline();
    return rts;

  def wr( self, str ):
    self.ser.write( str.encode("utf-8") );
    return;

  def close(self):
    self.ser.close();
    return;
