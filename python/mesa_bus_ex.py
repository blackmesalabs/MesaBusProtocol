#!python3
###################################################################################################
# Source file : mesa_bus_ex.py 
# Language    : Python 3.7 - may work with earlier and later 3.x versions.
# Author      : Kevin Hubbard    
# Description : Example Python to talke to bd_server and Mesa Bus.
# License     : GPLv3
#               This program is free software: you can redistribute it and/or modify
#               it under the terms of the GNU General Public License as published by
#               the Free Software Foundation, either version 3 of the License, or
#               (at your option) any later version.
#
#               This program is distributed in the hope that it will be useful,
#               but WITHOUT ANY WARRANTY; without even the implied warranty of
#               MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#               GNU General Public License for more details.
#
#               You should have received a copy of the GNU General Public License
#               along with this program.  If not, see <http://www.gnu.org/licenses/>.
# Notes       : PySerial for Python3 from https://pypi.python.org/pypi/pyserial/
# -------------------------------------------------------------------------------------------------
# History :
#   11.29.2024 : khubbard : Created. Forked from bd_shell.py
###################################################################################################
from common_functions import file2list;
from common_functions import list2file;

import sys;
import select;
import socket;
import time;
import os;
import random;
from time import sleep;
from os import path;


import class_lb_link;       # Access to LocalBus over MesaBus over serial
import class_lb_tcp_link;   # Access to LocalBus over TCP link to bd_server.py
import class_mesa_bus;      # Access to MesaBus over serial
import class_uart_usb_link; # Access to serial over USB COM type connection
#import class_cmd_proc;
#import class_spi_prom;      # Access to spi_prom.v over LocalBus
#import class_user;          # Example of user defined add on functions
#import class_ft600_usb_link;# Access to serial over USB3 FT600 type connection
#import class_sump2;         # Access to sump2.v logic analyzer engine in HW

def main():
  args = sys.argv + [None]*3;# args[0] is mesa_bus_ex.py
  var_dict = {};

  # If INI file exists, load it, otherwise create a default one and use it
  file_name = path.join( os.getcwd(), "mesa_bus_ex.ini");
  if ( ( path.exists( file_name ) ) == False ):
    ini_list =  ["bd_connection   = usb       # usb,usb3,pi_spi,tcp",
                 "bd_protocol     = mesa      # mesa,poke",
                 "tcp_port        = 21567     # 21567    ",
                 "tcp_ip_addr     = 127.0.0.1 # 127.0.0.1",
                 "usb_port        = COM4      # ie COM4",
                 "usb_baudrate    = 921600    # ie 921600",
                 "mesa_slot       = 00        # ie 00",
                 "mesa_subslot    = 0         # ie 0",    ];
    ini_file = open ( file_name, 'w' );
    for each in ini_list:
      ini_file.write( each + "\n" );
    ini_file.close();
    
  if ( ( path.exists( file_name ) ) == True ):
    ini_file = open ( file_name, 'r' );
    ini_list = ini_file.readlines();
    for each in ini_list:
      words = " ".join(each.split()).split(' ') + [None] * 4;
      if ( words[1] == "=" ):
        var_dict[ words[0] ] = words[2];

  # Assign var_dict values to legacy variables. Error checking would be nice.
  bd_connection =     var_dict["bd_connection"];
  com_port      =     var_dict["usb_port"];
  baudrate      = int(var_dict["usb_baudrate"],10);
  mesa_slot     = int(var_dict["mesa_slot"],16);
  mesa_subslot  = int(var_dict["mesa_subslot"],16);
  tcp_ip_addr   =     var_dict["tcp_ip_addr"];
  tcp_port      = int(var_dict["tcp_port"],10);

  # Establish connection to Backdoor Hardware 
  try:  
    if ( bd_connection == "tcp" ):
      bd  = class_lb_tcp_link.lb_tcp_link( ip = tcp_ip_addr, port = tcp_port );
      if ( bd.sock == None ):
        bd = None;
    elif ( bd_connection == "usb" ):
      usb = class_uart_usb_link.uart_usb_link( port_name=com_port,
                                               baudrate=baudrate  );
      mb  = class_mesa_bus.mesa_bus( phy_link=usb );
      bd  = class_lb_link.lb_link( mesa_bus=mb, slot=mesa_slot, 
                                   subslot=mesa_subslot );
  except:
    print("ERROR: Backdoor connection failed. Check hardware and ini file");
    sys.exit();

  dword = bd.rd( 0x00000000 )[0];      # Mesa Bus Read Example
  print("%08x" % dword );
  bd.wr( 0x00000004, [ 0x00000055 ] ); # Mesa Bus Write Example
  dword = bd.rd( 0x00000004 )[0];      # Mesa Bus Read Example
  print("%08x" % dword );

  return;


###############################################################################
try:
  if __name__=='__main__': main()
except KeyboardInterrupt:
  print('Break!')
# EOF
