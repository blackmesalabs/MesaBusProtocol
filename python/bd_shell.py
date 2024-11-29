#!python3
###################################################################################################
# Source file : bd_shell.py    
# Language    : Python 3.7 - may work with earlier and later 3.x versions.
# Author      : Kevin Hubbard    
# Description : Backdoor Shell, a UNIX shell like interface for writing and reading FPGA and ASIC 
#               registers sitting on a 32bit Local Bus.
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
#   01.01.2018 : khubbard : Created. Offshoot from original .NET Powershell 
# TODO: Need to figure out clean way to get slot and subslot working over TCP
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

import class_cmd_proc;

import class_spi_prom;      # Access to spi_prom.v over LocalBus
import class_lb_link;       # Access to LocalBus over MesaBus over serial
import class_lb_tcp_link;   # Access to LocalBus over TCP link to bd_server.py
import class_mesa_bus;      # Access to MesaBus over serial
import class_uart_usb_link; # Access to serial over USB COM type connection
#import class_ft600_usb_link;# Access to serial over USB3 FT600 type connection
#import class_sump2;         # Access to sump2.v logic analyzer engine in HW
import class_user;          # Example of user defined add on functions


def main():
  args = sys.argv + [None]*3;# args[0] is bd_shell.py
  title = "bd_shell 2019.11.05 - Black Mesa Labs - GPLv3";
  var_dict = {};
  cmd_history = [];

  import platform,os;
  os_sys = platform.system();  # Windows vs Linux
  if ( os_sys == "Windows" ):
    os.system("title "+title );# Give DOS-Box a snazzy title
  print("Welcome to "+title);


  # If INI file exists, load it, otherwise create a default one and use it
  file_name = path.join( os.getcwd(), "bd_shell.ini");
  if ( ( path.exists( file_name ) ) == False ):
    ini_list =  ["bd_connection   = usb       # usb,usb3,pi_spi,tcp",
                 "bd_protocol     = mesa      # mesa,poke",
                 "tcp_port        = 21567     # 21567    ",
                 "tcp_ip_addr     = 127.0.0.1 # 127.0.0.1",
                 "usb_port        = COM4      # ie COM4",
                 "usb_baudrate    = 921600    # ie 921600",
#                "search_path     = .,search_dir",
                 "scripts_path    = .,sump2_scripts,bd_scripts",
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

  # See if the search path directories exist, create if they don't
  search_path = var_dict["scripts_path"];
  paths     = search_path.split(',');
  for each_path in paths:
    if ( not os.path.exists( each_path ) ):
      print("Note: Creating %s" % each_path );
      os.makedirs( each_path );
 
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
    print("ERROR: Backdoor connection failed. Check hardware and bd_shell.ini");
    # Save variables sorted alphabetically by name to bd_shell.ini file
    rts = [];
    for (key,val) in sorted( var_dict.items() ):
      rts += ["%-30s = %s" % ( key, val ) ];
    list2file( "bd_shell.ini", rts );
    bd = None; # Support running CLI w/o hardware present
#   sys.exit();

  # Now load Plugin classes for PROM, SUMP2, Command Processing and User Code
  prom = class_spi_prom.spi_prom( lb_link = bd );
  user = class_user.user( lb_link = bd );

# sump2 = class_sump2.sump2( lb_link=bd, var_dict=var_dict );
  sump2 = None;

# cmd  = class_cmd_proc.cmd_proc( bd,prom,sump2,user,var_dict,sump2.wave_dict);
  cmd  = class_cmd_proc.cmd_proc( bd,prom,sump2,user,var_dict, None );

  # Other modules have their own help text which gets appended to the main cmd.help
  # help is a brief one line. Detailed help can be a paragraph and is brought up
  # with 'help foo' versus just 'help' for displaying brief help for all.
# cmd.help += sump2.help;
# cmd.detailed_help += sump2.detailed_help;
  cmd.help += user.help;
  cmd.detailed_help += user.detailed_help;
  cmd.help += prom.help;

  # Look for mesa_slot and mesa_subslot vars and issue as commands for bd_server
  mesa_list = [ "mesa_slot", "mesa_subslot" ];
  for each_key in mesa_list:
    if ( var_dict.get(each_key) != None ):
      value = var_dict[each_key];
      cmd_str = "%s %s" % ( each_key, value );
      if ( bd != None ):
        rts = cmd.proc( cmd_str );

  # Assign the sump2 defaults as bd_shell variables if unassigned
# for key in sump2.var_dflt:
#   if ( var_dict.get(key) == None ):
#     cmd_str = "%s = %s" % ( key, sump2.var_dflt[key] );
#     rts = cmd.proc( cmd_str );

  # If sump2.ini exists, use it in place of any bd_shell.ini defaults
# if ( os.path.exists( sump2.sump2_ini ) ):
#   print("Found %s - sourcing it " % sump2.sump2_ini );
#   cmd_list = file2list( sump2.sump2_ini );
#   for cmd_str in cmd_list: 
#     words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
#     # Filter out any GUI specific variables as to not clutter up env
#     if not any( each in words[0] for each in sump2.sump_cull_list ):
#       rts = cmd.proc( cmd_str );

  # If sump2_wave.txt exists, use it
# if ( os.path.exists( sump2.sump2_wave ) ):
#   print("Found %s - sourcing it " % sump2.sump2_wave );
#   cmd_list = file2list( sump2.sump2_wave );
#   for cmd_str in cmd_list: 
#     if not ( "-bundle" in cmd_str ):
#       rts = cmd.proc( cmd_str );

  # Look for sump startup script
  if ( var_dict.get("sump_script_startup") != None ):
    sump_script_startup = var_dict.get("sump_script_startup");
    if ( os.path.isfile(sump_script_startup)  ):
      print("Found %s - sourcing it " % sump_script_startup );
      cmd_list = file2list( sump_script_startup );
      for cmd_str in cmd_list: 
        rts = cmd.proc( cmd_str );

# # Look for sump shutdown script
# if ( var_dict.get("sump_script_shutdown") != None ):
#   sump_script_shutdown = var_dict.get("sump_script_shutdown");
#   if ( os.path.isfile(sump_script_shutdown)  ):
#     cmd_list = file2list( sump_script_shutdown );
#     for cmd_str in cmd_list: 
#       rts = cmd.proc( cmd_str );

# import curses;
# screen = curses.initscr();
# curses.noecho();
# curses.cbreak(); # Don't wait for ENTER
# screen.keypad(True); # Map arrow keys to special values
# try:
#   while ( True ):
#     char = screen.getch();
#     if ( char == ord('q') ):
#       break;
#     elif ( char == curses.KEY_LEFT ):
#       print("Left");
#     elif ( char == curses.KEY_RIGHT ):
#       print("Right");
# finally:
#   curses.nocbreak(); screen.keypad(0); curses.echo();
#   curses.endwin();
# import sys
# for line in sys.stdin.readlines():
#   print( ord(line) );


  # If there is no argument, then sit in a loop CLI style 
  if ( args[1] == None ):
    cmd_str = None;
#   while ( cmd_str != "" ):
    while ( True ):
      print("bd>",end="");
      cmd_str = input();
      rts = cmd.proc( cmd_str );
      if ( rts != None ):
        for each in rts:
          print("%s" % each );
    return;
  # If args[1] is a file, open it and process one line at a time
  elif ( path.exists( args[1] ) ):
    cmd_list = file2list( args[1] );
    for cmd_str in cmd_list: 
      rts = cmd.proc( cmd_str );
      if ( rts != None ):
        for each in rts:
          print("%s" % each );
  else:
  # If args[1] is not a file, just process the single command line args
    arg_str = filter( None, args[1:] );
    cmd_str = "";
    for each in arg_str:
      cmd_str += each + " ";
    rts = cmd.proc( cmd_str );
    if ( rts != None ):
      for each in rts:
        print("%s" % each );
  return;


###############################################################################
try:
  if __name__=='__main__': main()
except KeyboardInterrupt:
  print('Break!')
# EOF
