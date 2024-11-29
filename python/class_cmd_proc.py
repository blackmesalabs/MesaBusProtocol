#!python3
###############################################################################
# Source file : class_cmd_proc.py
# Language    : Python 3.3 or Python 3.5
# Author      : Kevin Hubbard
# Description : Process bd_shell commands
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
#   2018.08.28 : khubbard : Created
#   2019.04.30 : khubbard : Added sump wave as variable assignments
#   2019.08.07 : khubbard : Added support for # comments 
###############################################################################
import sys;
import os;
from os import path;

from common_functions import file2list;
from common_functions import list2file;


class cmd_proc:
  def __init__ ( self, bd, prom, sump2, user, var_dict, wave_dict ):
    self.bd          = bd;
    self.prom        = prom;
    self.sump2       = sump2;
    self.user        = user;
    self.cmd_history = [];
    self.var_dict    = var_dict;
    self.wave_dict   = wave_dict;
    ( self.help, self.detailed_help ) = self.init_help();
    return;

  def proc( self, cmd_str ):
    rts = [];
    cmd_str = (cmd_str.split("#") + [None])[0];
    if ( cmd_str == "" ):
      return rts;
#   print("cmd_str = >%s<" % cmd_str );
    
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    cmd_txt = words[0];
    valid_command = False;

    # Command History stuff
    if ( cmd_str != "" and cmd_str[0] != "!" ):
      self.cmd_history += [ cmd_str ];

    # Check if history command ( again, may want to replace ).
    if ( cmd_txt == "h" or cmd_txt == "history" ):
      rts = ["%d %s" % (i+1,str) for (i,str) in enumerate(self.cmd_history)];# 
      return rts;
    if ( cmd_txt == "!!" or cmd_txt[0] == "!" ):
      if ( cmd_txt == "!!" ):
        cmd_str = self.cmd_history[-1];
      else:
        cmd_str = self.cmd_history[int(cmd_txt[1:],10)-1];
      words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
      cmd_txt = words[0];


    # Check if sump2 wave description like "/event[0] -hidden -nickname foo"
    if ( words[0][0:1] == "/" ):
      # Remove any leading whitespace
      cmd_str = cmd_str.lstrip(' ');
      words = cmd_str.split(' ',1);# "/event[0]" and "-hidden -nickname foo"
      self.wave_dict[words[0]] = words[1];
      valid_command = True;
      return [];

    # Check if a manual wave assignment like "event[0] = foo_net"
    if ( (( "event[" in words[0] ) or ( "dword[" in words[0] )) and ( words[1] == "=" ) ):
      self.wave_dict["/"+words[0]] = "-nickname " + words[2];# Convert to wave format
      valid_command = True;
      return [];


    cmd_str = cmd_str.replace("=", " = ");

    # Check for "> filename" or ">> filename"
    pipe_file = None; cat_file = None;
    if ( ">" in cmd_str and ">>" not in cmd_str ):
      cmd_str = cmd_str.replace(">", " > ");
      words = " ".join(cmd_str.split()).split('>') + [None] * 4;
      cmd_str = words[0];
      pipe_file = words[1];
      pipe_file = pipe_file.replace(" ", "");
    elif ( ">>" in cmd_str ):
      cmd_str = cmd_str.replace(">>", " >> ");
      words = " ".join(cmd_str.split()).split('>>') + [None] * 4;
      cmd_str = words[0];
      cat_file = words[1];
      cat_file = cat_file.replace(" ", "");

    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    cmd_txt = words[0];

    # Check to see if this is a variable command 1st as may want to replace
    if ( words[1] == "=" ):
      valid_command = True;
      # Check for foo = 12 when foo == bar and assign bar = 12 keeping foo = bar
      # is "foo" in dictionary?
      if ( self.var_dict.get(words[0]) != None ):
        # grab its value "bar"
        prev_value = self.var_dict[ words[0] ];
        # is "bar" in dictionary ?
        if ( self.var_dict.get( prev_value ) != None ):
          self.var_dict[ prev_value ] = words[2];# assign 12 to "bar"
        else:
#         print("Assigning %s = %s" % ( words[0], words[2] ));
          self.var_dict[ words[0] ] = words[2];
      else:
#       print("Assigning %s = %s" % ( words[0], words[2] ));
        self.var_dict[ words[0] ] = words[2];

      # convert "mesa_subslot = e" to command "mesa_subslot e"
      if ( words[0][0:5] == "mesa_" ):
        cmd_str = cmd_str.replace("=","");
        words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
        cmd_txt = words[0];
    elif ( cmd_txt == "print" ):
      valid_command = True;
      rts = print("%s" % self.var_dict[ words[1] ]);
    elif ( cmd_txt == "env" ):
      valid_command = True;
      # Display the variables sorted alphabetically by name
      for (key,val) in sorted( self.var_dict.items() ):
        rts += ["%-16s : %s" % ( key, val ) ];
    elif ( cmd_txt == "h" or cmd_txt == "?" or cmd_txt == "help" ):
      rts = self.cmd_help( cmd_str );
      valid_command = True;

    else:
      # Replace any variables after word[0] with their dictionary replacement
      word_str = " ";
      for each_word in words[1:]:
        for key in self.var_dict:
          if ( each_word != None ):
            each_word = each_word.replace(key,self.var_dict[key]);
          else:
            each_word = "";
        word_str += each_word + " ";
      cmd_str = words[0] + word_str;
      words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
      cmd_txt = words[0];


    # Check if this is a variable and if variable is a {cmd;cmd} macro
#   if ( self.var_dict.get(cmd_txt) != None and words[1] == None and 
#        cmd_txt not in self.sump2.cmd_list ):
    if ( self.var_dict.get(cmd_txt) != None and words[1] == None ):
      macro_str = self.var_dict[cmd_txt];
      macro_words = macro_str.split(';');
      for each in macro_words:
        each = each.replace(" ", "");
        each = each.replace(";", "");
        if ( each != "" ):
          rts1 = self.proc( each );
          if ( rts1 != None ):
            rts += rts1;

    if ( cmd_txt == "source" ):
      valid_command = True;
      print("SOURCE %s %s" % ( cmd_txt, cmd_str ) );
      import os;
#     search_path = self.var_dict["search_path"];
      search_path = self.var_dict["scripts_path"];
      paths     = search_path.split(',');
      for each_path in paths:
        file_name = os.path.join( each_path, words[1] );
        if ( path.exists( file_name )):
          cmd_list = file2list( file_name );
          for cmd_str in cmd_list:
            rts1 = self.proc( cmd_str );
            if ( rts1 != None ):
              rts += rts1;
#       else:
#         print("ERROR File %s does not exist" % file_name );

    # Shell Commands that Mimic UNIX shells
    if ( cmd_txt == "manual" ):
      rts = self.cmd_manual();
      valid_command = True;
    elif ( cmd_txt == "q" or cmd_txt == "quit" or cmd_txt == "exit" ):
      rts = self.cmd_quit( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "vi" ):
      rts = self.cmd_vi( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "more" ):
      rts = self.cmd_more( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "ls" ):
      rts = self.cmd_ls( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "cd" ):
      rts = self.cmd_cd( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "cp" ):
      rts = self.cmd_cp( cmd_str );
      valid_command = True;
    elif ( cmd_txt == "pwd" ):
      rts = self.cmd_pwd( cmd_str );
      valid_command = True;
    elif ( cmd_txt[0:5] == "sleep" ):
      rts = self.cmd_sleep( cmd_str );
      valid_command = True;


    # MesaBus Commands
    elif ( cmd_txt == "mesa_slot" ):
      valid_command = True;
      if hasattr( self.bd, 'slot'):
        self.bd.slot = int( words[1], 16 );       # Local Serial Port
      else:
        self.bd.set_slot( int( words[1], 16 ));   # TCP to bd_server
    elif ( cmd_txt == "mesa_subslot" ):
      valid_command = True;
      if hasattr( self.bd, 'subslot'):
        self.bd.subslot = int( words[1], 16 );    # Local Serial Port
      else:
        self.bd.set_subslot( int( words[1], 16 ));# TCP to bd_server

    # LocalBus Commands
    elif ( cmd_txt == "r" or cmd_txt == "read" ):
      valid_command = True;
      rts = self.cmd_read( cmd_str );
    elif ( cmd_txt == "w" or cmd_txt == "write" ):
      valid_command = True;
      rts = self.cmd_write( cmd_str );

    # Commands defined in external class files
    # SUMP2 commands
#   if ( cmd_txt in self.sump2.cmd_list ):
    if False:
      valid_command = True;
      rts = self.sump2.proc_cmd( cmd_txt, cmd_str );
      if ( cmd_txt == "sump_acquire" ):
        # Look for sump shutdown script
        if ( self.var_dict.get("sump_script_shutdown") != None ):
          sump_script_shutdown = self.var_dict.get("sump_script_shutdown");
          import os;
          if ( os.path.isfile(sump_script_shutdown)  ):
            cmd_list = file2list( sump_script_shutdown );
            for cmd_str in cmd_list:
              rts = self.proc( cmd_str );

    # Wanted this to be a class_sump2 command, but it actually sources ext
    # files as scripts and processes them as commands. Couldn't figure out
    # how to have class_sump2 call class_cmd_proc, so here it is.
#   if ( cmd_txt == "sump_user_ctrl" and words[1] != "=" ):
    if False:
      valid_command = True;
      sump_user_ctrl_list = self.sump2.find_sump_user_ctrl_files();
      words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
      user_ctrl = words[1];# If No parm, display available user_ctrl files
      if ( user_ctrl == None ):
        sump_user_ctrl_list = self.sump2.select_list( sump_user_ctrl_list );
        for each in sump_user_ctrl_list:
          print( each );
      else:
        if ( user_ctrl in self.sump2.int_list ):
          user_ctrl = sump_user_ctrl_list[ int( user_ctrl, 10 ) ];
          print( user_ctrl );
          cmd_str = "source " + user_ctrl;
          rts = self.proc( cmd_str );


    # Example User defined commands 
    if ( cmd_txt in self.user.cmd_list ):
      valid_command = True;
      rts = self.user.proc_cmd( cmd_txt, cmd_str );

    # PROM Commands
    if ( cmd_txt in self.prom.cmd_list ):
      valid_command = True;
      rts = self.prom.proc_cmd( cmd_txt, cmd_str );

    # Send results to a file for ">" and ">>" piping
    if ( pipe_file != None ):
      list2file( pipe_file, rts );
      rts = [];
    if ( cat_file != None ):
      list2file( cat_file, rts, concat = True );
      rts = [];

    if ( valid_command == False ):
      rts += ["ERROR: Unknown command : %s " % cmd_str ];

    return rts;


  ##################################
  # Shell Stuff
  def cmd_help( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
   
    # Either display all the condensed help, or give detailed help on single topic 
    if ( words[1] == None ):
      return self.help;
    else:
      rts = [];
      for ( each_word, each_description ) in self.detailed_help:
        if ( each_word == words[1] ):
          rts = [each_description]; 
      return rts;

  def init_help( self ):
    r = [];
    r+=["#######################################################################################"];
    r+=["# bd_shell by Kevin M. Hubbard @ Black Mesa Labs. GPLv3                                "];
    r+=["# Hardware Local Bus Access commands                                                   "];
    r+=["#  r addr                : Read from addr                                              "];
    r+=["#  r addr num_dwords     : Read num_dwords starting at addr                            "];
    r+=["#  w addr data           : Write data to addr                                          "];
    r+=["#  w addr data data      : Write multiple data to addr                                 "];
    r+=["# Mesa Bus Access commands                                                             "];
    r+=["#  mesa_slot = n         : Assign mesa_slot to n                                       "];
    r+=["#  mesa_subslot = n      : Assign mesa_subslot to n                                    "];
    r+=["# File commands                                                                        "];
    r+=["#  source file           : Source a bd_shell script                                    "];
    r+=["#  more filename         : Display contents of filename                                "];
    r+=["#  vi filename           : Edit filename with default editor                           "];
    r+=["#  > filename            : Pipe a command result to filename                           "];
    r+=["#  >> filename           : Concat a command result to filename                         "];
    r+=["# Shell commands                                                                       "];
    r+=["#  cd dest               : Change Directory                                            "];
    r+=["#  cp src dest           : Copy file                                                   "];
    r+=["#  env                   : List all variables                                          "];
    r+=["#  foo = bar             : Assign value bar to variable foo                            "];
    r+=["#  ls                    : List files in current directory                             "];
    r+=["#  print foo             : Display value of variable foo                               "];
    r+=["#  pwd                   : Display current directory location                          "];
    r+=["#  sleep n               : Pause for n seconds                                         "];
    r+=["#  sleep_ms n            : Pause for n milliseconds                                    "];
    r+=["#  h or history          : Display command history                                     "];
    r+=["#  !!                    : Repeat last command from history                            "];
    r+=["#  !n                    : Repeat command n from history                               "];
    r+=["#  ? or help             : Display this help screen                                    "];
    r+=["#  help                  : Display list of commands or info on a specific command      "];
    r+=["#  manual                : Detailed manual                                             "];
    r+=["#  quit                  : Exit bd_shell                                               "];

    dh = [];
    dh+=[("mesa_slot",
           "The MesaBus protocol support serial daisy chaining up to 254 devices that are "      +\
           "self enumerated based on their position in the chain. The 1st device in a "          +\
           "MesaBus chain will be 'slot 0'. The mesa_slot command supports assigning a "         +\
           "different slot ( 0 to FE ) to be used for future bus access commands.      " )       ];
    dh+=[("mesa_subslot",
           "The MesaBus protocol supports 15 subslots within a slot. Nominally subslot 0 is "    +\
           "used for local bus access and subslot E is used for SPI configuration PROM." )       ];
    dh+=[("r",
           "The <r>ead command will read one or more DWORDs starting at the specified hex "      +\
           "address. If a 2nd parameter is supplied, it designates the number of DWORDs to read "+\
           "instead of reading the default single DWORD. Output of the <r>ead command are "      +\
           "32bit hexadecimal DWORD or DWORDs separated by a <LF>.\n"                            +\
           "Example:\n"                                                                          +\
           " bd>r 0 2\n"                                                                         +\
           " 00000011\n"                                                                         +\
           " 000012ab\n"                                                                         +\
           "This will read 0x00000011 from 0x0000000 and 0x000012ab from 0x00000004"            )];
    dh+=[("w",
           "The <w>rite command will write one or more DWORDs starting at the specified hex "    +\
           "address.\n"                                                                          +\
           "Example:\n"                                                                          +\
           " bd>w 00000010 aabbccdd 11223344\n"                                                  +\
           "This will write 0xaabbccdd to 0x00000010 and 0x11223344 to 0x00000014"              )];
    dh+=[("source",                                             
           "The 'source' command supports scripting via bd_shell commands in external files.\n"  +\
           "Example:\n"                                                                          +\
           " bd>source foo.txt\n"                                                                +\
           "This will interpret and execute all bd_shell commands inside file foo.txt."         )];
    dh+=[("sleep",                                              
           "The 'sleep' command supports pausing a script for specified number of seconds.\n"    +\
           "Example:\n"                                                                          +\
           " bd>sleep 5\n"                                                                       +\
           "This will pause for 5 seconds before continuing."                                   )];
    dh+=[("sleep_ms",                                           
           "The 'sleep_ms' command supports pausing script for specified number of millisecs.\n" +\
           "Example:\n"                                                                          +\
           " bd>sleep 100\n"                                                                     +\
           "This will pause for 256 milliseconds before continuing."                             )];
    dh+=[("tcp_ip_addr",                                        
           "When using bd_server.py, this specifies the IP address of the bd_server.py server,"  +\
           " typically 127.0.0.1 for the same machine but may also be a remote machine.\n"      )];
    dh+=[("tcp_port",                                        
           "The Berkeley Sockets port number shared by bd_server and bd_shell, typically 21567.")];
    dh+=[("bd_connection",                                      
           "backdoor connection to hardware. Either 'usb' for FTDI or 'tcp' for bd_server.")];
    dh+=[("bd_protocol",                                      
           "backdoor protocol used. 'mesa' for both 'usb' and 'tcp'.")];
    dh+=[("usb_port",                                      
           "Port number for FTDI VCP driver, Example 'COM4'.")];
    dh+=[("usb_baudrate",                                      
           "Baud rate for FTDI VCP driver, Example '921600'.")];

    return (r,dh);

  def cmd_quit( self, cmd_str ):
    # Save variables sorted alphabetically by name to bd_shell.ini file
    rts = [];
    for (key,val) in sorted( self.var_dict.items() ):
      rts += ["%-30s = %s" % ( key, val ) ];
    list2file( "bd_shell.ini", rts );
    print("Goodbye");
#   self.sump2.shutdown();
    sys.exit();

  def cmd_vi( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    import os;
    os.system( words[1] );# Note, this is blocking. Works on Windows only
    rts = [];
    return rts;

  def cmd_more( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    rts = file2list( words[1] );
    return rts;

  def cmd_ls( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    rts = [];
#   import os;
#   for ( root, dirs, files ) in os.walk("."):
#     rts += dirs;
#     rts += files;
    if ( words[1] == None ):
      words[1] = "*";
    import glob;
#   rts += glob.glob( words[1] );
    # Differentiate dirs from files with "/" just like Linux ls does.
    file_list = glob.glob( words[1] );
    for each in file_list:
      if ( os.path.isdir( each ) ):
        each = each + "/";
      rts += [ each ];
    return rts;

  def cmd_cp( self, cmd_str ):
    import shutil
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    shutil.copy2( words[1], words[2] );
    return [];

  def cmd_pwd( self, cmd_str ):
    import os;
    rts = [];
    rts += [ os.getcwd() ];
    return rts;

  def cmd_cd( self, cmd_str ):
    import os;
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    os.chdir( words[1] );
    return [];

  def cmd_sleep( self, cmd_str ):
    rts = [];
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    dur = int(words[1],16);
    if ( words[0] == "sleep_ms" ):
      dur = dur / 1000.0;
    import time;
    time.sleep( dur );
    return rts;


  ##################################
  # LocalBus Stuff
  def cmd_read( self, cmd_str ):
    rts = [];
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    addr = int(words[1],16);
    num_dwords = words[2];
    if ( num_dwords == None ):
      num_dwords = 1;
    else:
      num_dwords = int( num_dwords, 16 );
    try:
      rts = self.bd.rd( addr, num_dwords );
      txt_rts = [ "%08x" % each for each in rts ];# list comprehension
    except:
      txt_rts = [ "ERROR cmd_read() : Read of Hardware failed." ];
    return txt_rts;

  def cmd_write( self, cmd_str ):
    rts = [];
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    addr = int(words[1],16);
    data_list = [ int( each,16) for each in filter(None,words[2:]) ];
    try:
      rts = self.bd.wr( addr, data_list );
    except:
      rts = [ "ERROR cmd_write() : Write to Hardware failed." ];
    return rts;


  def cmd_manual( self ):
    r = [];
    r+=["###################################################################"];
    r+=["# bd_shell is a command line tool for writing and reading chip  "];
    r+=["# registers on a virtual 32bit PCI bus. Communication is usually"];
    r+=["# using Mesa Bus Protocol over 2 pins connected to a FTDI Cable."];
    r+=["# Configuration is done by editing the bd_shell.ini variables.  "];
    r+=["# [bd_shell.ini]                                                "];
    r+=["#  bd_connection : The connection type. Valid values for this   "];
    r+=["#   are 'usb' for a FTDI USB cable or 'tcp' for a bd_server.py  "];
    r+=["#   connection using TCP/IP socket communications.              "];
    r+=["#  bd_protocol   : Should be 'mesa'. This is the serial protocol"];
    r+=["#  tcp_port      : Should be '21567' unless conflicts with other"];
    r+=["#  tcp_ip_addr   : Should be '127.0.0.1' for localhost packets. "];
    r+=["#  usb_port      : COM port assigned to FTDI cable, like 'COM4' "];
    r+=["#  baud_rate     : '921600' typically for maximum compatibility "];
    r+=["#  mesa_slot     : '00' typically for single Mesa Bus device.   "];
    r+=["#  mesa_subslot  : '0' for LocalBus or 'e' for SPI PROM bus.    "];
    r+=["# Directories:                                                  "];
    r+=["#  ./bd_scripts    : Directory for bd_shell script files        "];
    r+=["#  ./sump2_scripts : Source directory for SUMP2 scripts to run  "];
    r+=["#  ./sump2_ram     : Output directory for downloaded SUMP2 RAM  "];
    r+=["#  ./sump2_vcd     : Output directory for SUMP2 VCD files       "];
    return r;
# EOF
