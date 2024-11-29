#!python3
###############################################################################
# Source file : bd_server.py
# Language    : Python 3.3 or Python 2.7
# Author      : Kevin M. Hubbard 
# Description : A TCP Socket Server for Backdoor interfacing to hardware. 
#               This provides a common software interface (TCP Sockets) for 
#               executables and scripts to access Hardware without having 
#               device driver access to USB via FTDI USB serial cable.
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
#       -------------             --------------            
#      |             |           |              |<-pyserial-> USB Backoor
#      |  User App   |<-sockets->| bd_server.py |
#      |exe or script|           |              |
#       -------------             --------------               
#
# PySerial for Python3 from:
#   https://pypi.python.org/pypi/pyserial/
# -----------------------------------------------------------------------------
# History :
#   01.23.2014 : khubbard : Created 
#   03.06.2014 : khubbard : Sleep feature to prevent CPU spinning on idle.
#   03.10.2014 : khubbard : Merged bd_server3.py and bd_server2.py into one.
#   03.12.2014 : khubbard : Fixed broken reads - problem with num_dwords
#   05.22.2014 : khubbard : Fixed backwards compatibility with Python2       
#   05.29.2014 : khubbard : Send !! after sleep to USB for HW power cycling  
#   05.29.2014 : khubbard : Dont crash on serial port timeouts
#   05.29.2014 : khubbard : Improved startup error handling.   
#   06.03.2014 : khubbard : USB Posted Writes for 16x performance   
#   06.03.2014 : khubbard : TCP Socket Write Combining    
#   06.03.2014 : khubbard : New repeat address Write Bursting ("W") command.
#   06.20.2014 : khubbard : More verbose error handling with import traceback
#   07.17.2014 : khubbard : Added "!!" support for unlocking Poke after reboot
#   07.18.2014 : khubbard : Added "rt" register test command
#   09.25.2014 : khubbard : Improved Sleep, Wake and !!      
#   07.21.2016 : khubbard : Added MesaBus support. Switch to ini config file
#   07.22.2016 : khubbard : Pad DWORDs on "k" read-multiple command with " ".
#   09.06.2016 : khubbard : Python 3.5 cast len(payload)/2 to int
#   08.14.2024 : khubbard : Accept 'k' with Null for N-1 Times.              
#   08.14.2024 : khubbard : AES-256 Authentication and E2E Encryption added.
###############################################################################
import sys;
import select;
import socket;
import time;
import os;

#from SimpleXMLRPCServer import SimpleXMLRPCServer
#from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
# Restrict to a particular path.
#class RequestHandler(SimpleXMLRPCRequestHandler):
#  rpc_paths = ('/RPC2',)
#def xmlrpc_function(x, y):
#  status = 1+x+y;
#  result = [5, 6, [4, 5]]
#  return (status, result)


def main():
  args = sys.argv + [None]*3;# Example "bd_server.ini"
  vers          = "08.14.2024";
  auth          = "khubbard";
  posted_writes = True;# USB Only - speeds up back2back writes 16x

  # If no ini file is specified in ARGS[1], look for bd_server.ini in CWD.
  file_name = os.path.join( os.getcwd(), "bd_server.ini");
  if ( args[1] != None and os.path.exists( args[1] ) ):
    file_name = args[1];

  # If it exists, load it, otherwise create a default one and then load it.
  if ( ( os.path.exists( file_name ) ) == False ):
    ini_list =  ["bd_connection      = usb     # usb",
                 "bd_protocol        = mesa    # mesa,poke",
                 "usb_port           = COM4    # ie COM4",
                 "tcp_port           = 21567   # ie 21567",
                 "baudrate           = 921600  # ie 921600",
                 "mesa_slot          = 00      # ie 00",
                 "aes_authentication = 0       # ie 1",
                 "aes_e2e_encryption = 0       # ie 1",
                 "aes_key            = 0001020304050607" + \
                                      "08090a0b0c0d0e0f" + \
                                      "1011121314151617" + \
                                      "18191a1b1c1d1e1f",# AES-256 Key
                 "mesa_subslot       = 0       # ie 0",
                 "debug_bd_en        = 0       # ie 0,1",
                 "debug_tcp_en       = 0       # ie 0,1",  ];
    ini_file = open ( file_name, 'w' );
    for each in ini_list:
      ini_file.write( each + "\n" );
    ini_file.close();

  ini_hash = {};
  ini_hash["aes_authentication"] = "1";
  ini_hash["aes_e2e_encryption"] = "1";
  ini_hash["aes_key"] = "0001020304050607" + \
                        "08090a0b0c0d0e0f" + \
                        "1011121314151617" + \
                        "18191a1b1c1d1e1f";# AES-256 Default Key
    
  if ( ( os.path.exists( file_name ) ) == True ):
    ini_file = open ( file_name, 'r' );
    ini_list = ini_file.readlines();
    for each in ini_list:
      words = " ".join(each.split()).split(' ') + [None] * 4;
      if ( words[1] == "=" ):
        if ( words[0][0:1] != "#" ):
          ini_hash[ words[0] ] = words[2];

  # Assign ini_hash values to legacy variables. Error checking would be nice.
  tcp_log_en = False;
  bd_log_en  = False;
  if ( ini_hash["debug_tcp_en"] == "1" ):
    tcp_log_en = True;
    tcp_log    = open ( 'bd_server_tcp_log.txt', 'w' );
  if ( ini_hash["debug_bd_en"] == "1" ):
    bd_log_en = True;
    bd_log    = open ( 'bd_server_bd_log.txt', 'w' );
  bd_type      = ini_hash["bd_connection"].lower();
  bd_protocol  = ini_hash["bd_protocol"].lower();
  com_port     = ini_hash["usb_port"];
  tcp_port     = int(ini_hash["tcp_port"],10);
  baudrate     = int(ini_hash["baudrate"],10);
  mesa_slot    = int(ini_hash["mesa_slot"],16);
  mesa_subslot = int(ini_hash["mesa_subslot"],16);

  aes_key      = int(ini_hash["aes_key"],16);
  aes_authentication = int(ini_hash["aes_authentication"],10);
  aes_e2e_encryption = int(ini_hash["aes_e2e_encryption"],10);
    
  os.system('cls');# Win specific clear screen
  print("------------------------------------------------------------------" );
  print("bd_server.py "+vers+" by "+auth+".");

  # Establish Python is version 2 or 3
  if ( sys.version_info[0] != 2 and sys.version_info[0] != 3 ):
    print(" [FAIL] bd_server.py running on Python"+str( sys.version_info[0] ));
    abort();
  print(" [OK]   bd_server.py running on Python"+str( sys.version_info[0] ));

  # Establish TCP Socket Connection
  try:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM );
    server_socket.bind(('', tcp_port ));
    server_socket.listen(5);
    host_ip = socket.gethostbyname( socket.gethostname() );
    print(" [OK]   Serving TCP Socket "+str(tcp_port)+" on "+str(host_ip));
  except:
    print(" [FAIL] Serving TCP Socket "+str(tcp_port)+" on "+str(host_ip));
    abort();

  # Establish Hardware Connection
  try:
    if True:
      if ( bd_protocol == "poke" ):
        hw_bridge = Backdoor_Poke_UART( port_name=com_port, baudrate=baudrate,
                                        posted_writes=posted_writes );
      else:
        hw_bridge = Backdoor_Mesa_UART( port_name=com_port, baudrate=baudrate,
                                        slot=mesa_slot, subslot=mesa_subslot );

    print(" [OK]   Connection to " + bd_type + " " + com_port );
  except:
    print(" [FAIL] Connection to " + bd_type + " " + com_port );
    abort();

  print(" [OK]   bd_server.py is five-by-five" );


  # Establish AES-256 for Authentication and End-2-End Encryption using aes.py
  if True:
    rej_rem = False;# Accept remote Clients by default unless AES is enabled
    if aes_authentication == 1 or aes_e2e_encryption == 1:
      try:
        from aes import AES;# See https://github.com/Joshua-Riek/AES
        aes = AES(aes_key);# 256bit hex number
        if aes_e2e_encryption == 1:
          aes_e2e = aes;# e2e means End-2-End and will encrypt+decrypt ALL packets
        else:
          aes_e2e = None;# AES Authentication only ( performance thing )
        print(" [OK]   AES-256 Installation" );
      except:
        aes     = None;
        aes_e2e = None;
        rej_rem = True;# Reject all remote Clients as AES-256 failed to install
        print(" [FAIL] AES-256 Installation" );
      print(" [%d]    AES-256 Authentication" % aes_authentication );
      print(" [%d]    AES-256 E2E Encryption" % aes_e2e_encryption );
    else:
      aes     = None;
      aes_e2e = None;

  print("------------------------------------------------------------------" );
  print( " bd_client <-> TCP Sockets <-> bd_server <->"+  \
          " "+com_port+" "+ "<-> Hardware " );
  print("------------------------------------------------------------------" );
  print("Press Ctrl+Break to terminate");      

# server = SimpleXMLRPCServer(( "157.226.13.36" , 8000),
# server = SimpleXMLRPCServer(("localhost", 8000),
# server = SimpleXMLRPCServer(("localhost", 21567),
#                           requestHandler=RequestHandler);
# server.register_function(xmlrpc_function);
# server.serve_forever();



  ##############################
  # Main TCP Server Loop 
  ##############################
  read_list = [server_socket];
  run = True;
  # Sit in a loop listening for TCP traffic and build up a full packet per 
  # Backdoor Packet Protocol. Once a full packet is received, translate
  # it to a bus command, wait for a response and ACK back over TCP.
  # A packet begins with 8 ASCII hex nibbles, example "00000010" that indicate 
  # the number of bytes in the payload. Thank Nagle for that.
  # WARNING: Once a connection is established, this loop will spin up the CPU.
  # Prevent this from happening by calling sleep after a long idle period.
  idle_cnt = 0;
  idle_sleep_timeout  =  5000000; # About 15 seconds, varies on CPU speed
  sleep_jk            =  True;
  client_list_dict = {};# Keep track of Authentication status of each client
  challenge_list_dict = {};# Keep track of challenge numbers sent to multiple clients

  while ( run == True ):
    readable, writable, errored = select.select(read_list, [], []);
    for s in readable:
      if s is server_socket:
        client_socket, address = server_socket.accept();
        read_list.append(client_socket);
#       print("New connection established from %s" % str(address));
        raddr = address;# ( "ip", port );
        packet_jk  = False;
        packet_len = 0;
        packet_buf = "";

        # When a new client connects, decide what security needs to be enforced.
        if raddr[0] == "127.0.0.1":
          print("New Client %s is localhost : AES-256 Authentication not required." % str(raddr));
          client_list_dict[ raddr ] = "localhost"; 
        elif raddr[0] != "127.0.0.1" and rej_rem == True:
          print("New Client %s rejected due to lack of AES-256 on server." % str(raddr));
          client_list_dict[ raddr ] = "rejected";
        elif aes_authentication == 1:
          print("New Client %s : AES-256 Authentication is required." % str(raddr));
          client_list_dict[ raddr ] = False;
        elif aes_authentication == 0:
          print("New Client %s : AES-256 Authentication is disabled." % str(raddr));
          client_list_dict[ raddr ] = True;

      else:
        rx_str = s.recv(1024);
        if rx_str:
          time_now = int( time.time() );# UNIX time in seconds
          idle_cnt = 0;
          if ( sleep_jk == True ):
            sleep_jk =  False;
            # As a courtesy ( not required ) after sleeping, send a Backdoor
            # unlock command in case the hardware was reset or power cycled
            if ( isinstance( hw_bridge, Backdoor_Poke_UART ) ):# Vs PCIe
              print("Waking");
              hw_bridge.ser.flushOutput();
              hw_bridge.ser.flushInput();
              hw_bridge.ser.write( "!!".encode("utf-8"));

          packet_buf += rx_str.decode("utf-8");# Conv Byte Array to String
          if ( tcp_log_en ):
            tcp_log.write( "RX:"+packet_buf+"\n" );
          if ( packet_jk == False and ( len( packet_buf ) > 8 ) ):
            try:
              packet_len = int(packet_buf[0:8],16);# "00000012" to 0x00000012
            except:
              print("!Es muy mala! - Packet Header is corrupted.");
            packet_buf = packet_buf[8:];# Remove Header
            packet_jk  = True;
          while ( packet_jk == True and ( len(packet_buf) >= packet_len ) ):
            payload    = packet_buf[0:packet_len];# An entire packet
            packet_buf = packet_buf[packet_len:]; # Any remainder (next packet)
            packet_jk  = False;
            packet_len = 0;

            # See if the remainder has enough to start new packet
            if ( packet_jk == False and ( len( packet_buf ) > 8 ) ):
              try:
                packet_len = int( packet_buf[0:8], 16 );
              except:
                print("ERROR: Packet Header is corrupted.");
              packet_buf = packet_buf[8:];# Remove Header
              packet_jk  = True;

            # Now Process the Packet
#           print("RX: Payload is %s" % payload );
            raddr = s.getpeername();# Client ("IP",port)
            authenticated = client_list_dict[ raddr ];# Is THIS Client authenticated?
            if authenticated == False:
              if aes_e2e != None:
                e2e = True;# Request End-2-End encryption from client post authentication
              else:
                e2e = False;
              rts = process_aes_authentication( payload, aes,e2e, s, client_list_dict, challenge_list_dict );
              if rts == False:
                s.close();
                read_list.remove(s);
            elif authenticated != "rejected":
              if authenticated == "localhost":
                aes_e2e_client = None;# No E2E encryption for localhost clients
              else:
                aes_e2e_client = aes_e2e;# E2E encryption based on bd_server.ini settings
              rts = process_payload( hw_bridge, payload, aes_e2e_client );
#             print("TX: Payload is %s" % rts );
              if ( bd_log_en ):
                bd_log.write( "RX:"+payload+"\n" );
                bd_log.write( "TX:"+rts+"\n" );
              s.send( process_response( rts, aes_e2e_client ));
          # while ( packet_jk == True and ( len(packet_buf) >= packet_len ) ):
        else:
          # Prevent CPU from staying spun up after a period of no TCP traffic
          # Note - this only happens after a connection has been closed.
          if ( idle_cnt == (idle_sleep_timeout-1) ):
            print("Sleeping");
            sleep_jk = True;
          if ( idle_cnt == idle_sleep_timeout ):
            time.sleep(0.01);# 10ms sleep
          else:
            idle_cnt+=1;
        # if rx_str:
      # if s is server_socket:
    # for s in readable:
  # while ( run == True ):
# def main():

def abort():
  print("");
  import traceback;
  traceback.print_exc();
  input("Press <ENTER> to exit");# Pause to display 1st print message

def rol( val, shift_bits, max_bits ):
  rts = (val << shift_bits%max_bits) & (2**max_bits-1) | \
        ((val & (2**max_bits-1)) >> (max_bits-(shift_bits%max_bits)));
  return rts;

def ror( val, shift_bits, max_bits ):
  rts = ((val & (2**max_bits-1)) >> shift_bits%max_bits) | \
        (val << (max_bits-(shift_bits%max_bits)) & (2**max_bits-1))
  return rts;


##############################################################################
# process_aes_authentication() : Do the AES Authentication handshake
# Until authentication is established, only accept "opensesame" and "response"
#  [ Client ]                                       [ Server ]
#                      open_connection ->
#                  "opensesame"(encrypted) ->
#                   <- "challenge 255"
#                      "response FF" ->
#               <- "Greetings, ... e2e is required"
def process_aes_authentication( payload, aes, e2e, s, client_list_dict, challenge_list_dict ):
  raddr = s.getpeername();# Client ("IP",port)
  from_txt = payload;
  try:
    payload = aes.decrypt( payload );
  except:
    payload = "";# Probably wasn't an encrypted string, but clear text
  to_txt = payload;
  print("RX: %s => %s" % ( from_txt, to_txt ) );
  words = " ".join(payload.split()).split(' ') + [None] * 2;

  if words[0] == "opensesame":
    time_now = int( time.time() );# UNIX time in seconds
    # Make a challenge random number for this client
    import random;
    rnd_int = random.randint(0, 0xFFFFFFFF );
    challenge_list_dict["%d,%s" %(rnd_int,str(raddr))] = time_now;
    s.send( process_response("challenge %d\n" % rnd_int, aes));

    # Garbage collect challenge list and remove any old challenges > 5sec
    key_del_list = [];
    for key in challenge_list_dict:
      time_then = challenge_list_dict[ key ];
      if ( time_now - time_then ) > 5 :
        key_del_list += [ key ];
    for key in key_del_list:
      print("Deleting old AES-256 challenge %s" % str(key) );
      del challenge_list_dict[ key ];
    
  elif words[0] == "response":
    try:
      rsp_int = int( words[1], 16 );# Response is a 32bit Hex of Challenge Integer
#     print("Response %s" % words[1]);
    except:
      rsp_int = 0;

    key = "%d,%s" % ( rsp_int, raddr );
    if challenge_list_dict.get( key ) != None:
      print("Client %s : AES-256 Authentication Accepted" % str(raddr) );
      if e2e == True:
        txt = " e2e is required.";
      else:
        txt = "";
      s.send(process_response("Greetings, Professor Falken."+txt+"\n",aes));
      client_list_dict[ raddr ] = True;
      del challenge_list_dict[ key ];
    else:
      print("Client %s : AES-256 Authentication Rejected" % str(raddr) );
      return False;
  else:
    print("Client %s : Access Denied due to lack of AES-256 Authentication.");
    return False;
  return True;


##############################################################################
# process_response() : Convert ASCII response to TCP Packet with Header info
def process_response( response, aes_e2e ):
  if aes_e2e != None:
    from_txt = response;
    response = aes_e2e.encrypt( response );
    to_txt   = response;
    print("TX: %s => %s" % ( from_txt, to_txt ) );
  pkt_size = len( response );# How many bytes
  pkt_size = "%08x" % pkt_size;# 0x00000012 to "00000012"
  bin_data = ( pkt_size + response ).encode("utf-8");# 
  return bin_data;


##############################################################################
# process_payload() : Bridge between TCP Socket and Backdoor Poke
# process the Payload. It is a single simple ASCII backdoor command like:
# "w 00000000 aa55aa55" or "r 0000001c"
# Note: Also implements new Poke "loop read" command "k" for reading same
# address multiple times. This dramatically speeds up SUMP access as all data
# is read from single 32bit PCIe register.
# Note: Does not handle burst writes or reads. Keeping it simple to start out.
def process_payload( bd, payload, aes_e2e ):
  if aes_e2e != None:
    from_txt = payload;
    payload = aes_e2e.decrypt(payload);
    to_txt = payload;
    print("RX: %s => %s" % ( from_txt, to_txt ) );

  line_list = payload.rstrip("\n").split("\n");
  rts = "";
  for each_line in line_list:
    cmd_list = each_line.split()+[None]*10;#"w 0 1" to a list of cmd,addr,data
    # 'w' : Write a single dword
    if ( cmd_list[0] == "w" ):
      addr = ( int( cmd_list[1], 16) );
      data_list = [];
      data_list_str = cmd_list[2:];
      for each in data_list_str[:]:
        if ( each != None ):
          data_list.append( int( each, 16 ));
      bd.wr( addr, data_list );

    # 'W' : Write multiple dwords to same address
    # Backdoor has a special command for this
    elif ( cmd_list[0] == "W" ):
      addr = ( int( cmd_list[1], 16) );
      data_list = [];
      data_list_str = cmd_list[2:];
      for each in data_list_str[:]:
        if ( each != None ):
          data_list.append( int( each, 16 ));
      if True:
        bd.wr_repeat( addr, data_list );

    # Read one or many dwords
    elif ( cmd_list[0] == "r" ):
      addr = ( int( cmd_list[1], 16) );
      len = 0x0;# Single DWORD
      if ( cmd_list[2] != None ):
        if ( cmd_list[2] != "" ):
          len  = ( int( cmd_list[2], 16) );
      data_list = bd.rd( addr, (len+1) );
      rts = "";
      for each in data_list:
        rts += "%08x " % each;
      rts = rts.rstrip();

    # Read repeat a single dword address multiple times ( speeds up SUMP )
    # This is a Backdoor command, 
    elif ( cmd_list[0] == "k" ):
      addr = ( int( cmd_list[1], 16) );
#     data = ( int( cmd_list[2], 16) );# How many times to read N-1
      data = 0x0;# Single Read default
      if ( cmd_list[2] != None ):
        if ( cmd_list[2] != "" ):
          data  = ( int( cmd_list[2], 16) );

      if True:
#       print("%08x %08x" % ( addr, data ) );
        data_list = bd.rd_repeat( addr, data );
        rts = "";
        for each in data_list:
#         rts += "%08x" % each;
#       rts = rts.rstrip();
          rts += "%08x " % each;# New 07_22_2016
      rts = rts.rstrip();

    # rt Register Test
    elif ( cmd_list[0] == "rt" ):
      addr = ( int( cmd_list[1], 16) );
      dur  = ( int( cmd_list[2], 16) );
      good_cnt = 0; wr_data = 0xF08155AA;
      old_data = bd.rd( addr, 0x1 )[0];
      for k in range( dur ):
        bd.wr( addr, [ wr_data ] );
        rd1_data = bd.rd( addr, 0x1 )[0];
        rd2_data = bd.rd( addr, 0x1 )[0];
        if ( rd1_data == wr_data & rd2_data == wr_data ):
          good_cnt +=1;
        # If Loop is small, display results to console
        if ( dur < 64 ):
          my_str = "".join([" %08x :" % addr] +    \
                      [" %08x :" % wr_data]  +  \
                      [" %08x" % rd1_data] +    \
                      [" %08x" % rd2_data]);
          print( my_str );
        wr_data = ror(wr_data,1,32);# Rotate Test Data 
      bd.wr( addr, [ old_data ] );# Put original value back in
      rts = "%08x" % good_cnt;

    # bs BitSet
    elif ( cmd_list[0] == "bs" ):
      addr = ( int( cmd_list[1], 16) );
      bit  = ( int( cmd_list[2], 16) );
      old_data = bd.rd( addr, 0x1 );
      new_data = old_data[0] | bit;
      bd.wr( addr, [new_data] );

    # bc BitClear
    elif ( cmd_list[0] == "bc" ):
      addr = ( int( cmd_list[1], 16) );
      bit  = ( int( cmd_list[2], 16) );
      old_data = bd.rd( addr, 0x1 );
      new_data = old_data[0] & ~bit;
      bd.wr( addr, [new_data] );
    
    # Configure the S3 Hubbard board FPGA
    elif ( cmd_list[0] == "configure" ):
      if ( isinstance( bd, Backdoor_Poke_UART ) ):# Vs PCIe
        file_name = cmd_list[1];
        bd.configure( file_name );

    # Accept MesaBus specific slot commands 
    elif ( cmd_list[0] == "mesa_slot" ):
      if ( isinstance( bd, Backdoor_Mesa_UART ) ):# Vs PCIe
        mesa_slot = int(cmd_list[1],16);
        print("mesa_slot = %02x" % mesa_slot );
        bd.slot = mesa_slot;

    # Accept MesaBus specific slot commands 
    elif ( cmd_list[0] == "mesa_subslot" ):
      if ( isinstance( bd, Backdoor_Mesa_UART ) ):# Vs PCIe
        mesa_subslot = int(cmd_list[1],16);
        print("mesa_subslot = %01x" % mesa_subslot );
        bd.subslot = mesa_subslot;

    # Send a BangBang to unlock poke hardware 
    elif ( cmd_list[0] == "!!" ):
      if ( isinstance( bd, Backdoor_Poke_UART ) ):# Vs PCIe
        bd.ser.flushOutput();
        bd.ser.flushInput();
        bd.ser.write( "!!".encode("utf-8"));

    # Nuke the socket from orbit. It's the only way to be sure.
    elif ( cmd_list[0] == "q" ):
      bd.close();
      s.close();
      read_list.remove(s);

  return rts;


###############################################################################
# Routines for Reading and Writing Payloads over MesaBus
# A payload is a series of bytes in hexadecimal string format. A typical use
# for MesaBus is to transport a higher level Local Bus protocol for 32bit
# writes and reads. MesaBus is lower level and transports payloads to a
# specific device on a serial chained bus based on the Slot Number.
# More info at : https://blackmesalabs.wordpress.com/2016/03/04/mesa-bus/
class mesa_bus:
  def __init__ ( self, port ):
    self.port = port;# See com_link.py
    self.port.wr("\n");# For autobaud

  def wr( self, slot, subslot, cmd, payload ):
#   preamble  = "\nFFF0";
    preamble  = "F0";
    slot      = "%02x" % slot;
    subslot   = "%01x" % subslot;
    cmd       = "%01x" % cmd;
    num_bytes = "%02x" % int( len( payload ) / 2 );
    mesa_str  = preamble + slot + subslot + cmd + num_bytes + payload + "\n";
    self.port.wr( mesa_str );
    return;

  def rd( self ):
    rts = self.port.rd();
    return rts;


###############################################################################
# Serial port class for sending and receiving ASCII strings : MesaBus only
class com_link:
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

  def rd( self ):
    rts = self.ser.readline();
    return rts;

  def wr( self, str ):
    self.ser.write( str.encode("utf-8") );
    return;


###############################################################################
# Protocol interface for MesaBus over a UART PySerial connection.
class Backdoor_Mesa_UART:
  def __init__ ( self, port_name, baudrate, slot, subslot ):
    self.com_link = com_link( port_name=port_name,baudrate=baudrate);
    self.mesa_bus = mesa_bus( self.com_link);# Establish MesaBus link
    self.slot      = slot;
    self.subslot   = subslot;
    self.dbg_flag  = False;

  def wr_repeat(self, addr, data):
    self.wr( addr, data, repeat = True );

  def wr(self, addr, data, repeat = False ):
    # LocalBus WR cycle is a Addr+Data 8byte payload
    # Mesabus has maximum payload of 255 bytes, or 63 DWORDs.
    # 1 DWORD is LB Addr, leaving 62 DWORDs available for data bursts
    # if data is more than 62 dwords, parse it into multiple bursts
    each_addr = addr;
    data_list = data;
    if ( repeat == False ):
      mb_cmd = 0x0;# Burst Write
    else:
      mb_cmd = 0x2;# Write Repeat ( Multiple data to same address )

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
          each_addr +=4;
      self.mesa_bus.wr( self.slot, self.subslot, mb_cmd, payload );
    return;

  def rd_repeat( self, addr, num_dwords=1 ):
#   rts = self.rd( addr, num_dwords  , repeat = True );
    rts = self.rd( addr, num_dwords+1, repeat = True );
    return rts;

  def rd( self, addr, num_dwords=1, repeat = False ):
    dwords_remaining = num_dwords;
    each_addr = addr;
    if ( repeat == False ):
      mb_cmd = 0x1;# Normal Read 
    else:
      mb_cmd = 0x3;# Read  Repeat ( Multiple data to same address )
    rts = [];
    rts_dword = "00000000";
    while ( dwords_remaining > 0 ):
      if ( dwords_remaining > 62 ):
        n_dwords = 62;
        dwords_remaining -= 62;
      else:
        n_dwords = dwords_remaining;
        dwords_remaining = 0;

      # LocalBus RD cycle is a Addr+Len 8byte payload to 0x00,0x0,0x1
      payload = ( "%08x" % each_addr ) + ( "%08x" % n_dwords );
      self.mesa_bus.wr( self.slot, self.subslot, mb_cmd, payload );
      rts_mesa = self.mesa_bus.rd();
      # The Mesa Readback Ro packet resembles a Wi Write packet from slot 0xFE
      # This is to support a synchronous bus that clocks 0xFFs for idle
      # This only handles single DWORD reads and checks for:
      #   "F0FE0004"+"12345678" + "\n"
      #   "04" is num payload bytes and "12345678" is the read payload
      if ( len( rts_mesa ) > 8 ):
        rts_str = rts_mesa[8:];# Strip the FOFE0004 header
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
        print("ERROR: Invalid LocalBus Read >" + rts_mesa + "<");
        rts_mesa = self.mesa_bus.rd();
        print("ERROR2: Invalid LocalBus Read >" + rts_mesa + "<");
        if ( self.dbg_flag == "debug" ):
          sys.exit();
        rts += [ 0xdeadbeef ];
      if ( repeat == False ):
        each_addr += ( 4 * n_dwords );
    return rts;


  # This sends a locally referenced top.bit binary file to 
  # S3 Hubbard Board FPGA for configuration over Backdoor.
  def configure(self, file_name ):
    print("bd.configure() " + file_name);
    try:
      if ( file_name[-2:] != "gz" ):
        file_in = open ( file_name, 'rb' );# Read in binary top.bit file
        while True:
          packet = file_in.read( 4096 );   # 4K at a time
          if packet:
            self.com_link.write( packet );     # send out to serial port
          else:
            break;
        file_in.close();
      else:
        import gzip;
        file_in = open( file_name , 'rb' );
        file_in_gz = gzip.GzipFile( fileobj= file_in,mode='rb' );
        while True:
          packet = file_in_gz.read( 4096 );   # 4K at a time
          if packet:
            self.com_link.write( packet );     # send out to serial port
          else:
            break;
        file_in_gz.close();
        file_in.close();
      self.com_link.flushOutput();
      self.com_link.flushInput();
#     self.ser.write("!!");
#     rts = self.ser.readline();
      print("bd.configure() Complete");
    except:
      print("bd.configure() FAILED!");
    rts = "\n";
    return [rts];

  def close(self):
    self.com_link.flushOutput();
    self.com_link.flushInput();
    self.com_link.close()

  def __del__(self):
    try:
      self.com_link.close()
    except:
      raise RuntimeError("Backdoor ERROR: Unable to close COM Port!!")


###############################################################################
# Protocol interface for Poke over a UART PySerial connection.
# Note: Enabling posted_writes decreased write to write gaps from 16ms to 1ms
#       This feature doesn't wait for serial port <ACK> and instead just flushes
class Backdoor_Poke_UART:
  def __init__ ( self, port_name, baudrate, posted_writes ):
    try:
      import serial;
    except:
      raise RuntimeError("ERROR: PySerial from sourceforge.net is required");
      raise RuntimeError(         
         "ERROR: Unable to import serial\n"+
         "PySerial from sourceforge.net is required for USB connection.");
    try:
      self.ser = serial.Serial( port=port_name, baudrate=baudrate,
                               bytesize=8, parity='N', stopbits=1,
                               timeout=1, xonxoff=0, rtscts=0,     );
      self.port = port_name;
      self.baud = baudrate;
      self.posted_writes = posted_writes;
      self.ser.flushOutput();
      self.ser.flushInput();
      self.ser.write( "!!".encode("utf-8"));
      self.ser.write( "E 8\n".encode("utf-8") );
      self.ack_state = True;
      rts = self.ser.readline();

    except:
      raise RuntimeError("ERROR: Unable to open USB COM Port "+port_name)

  def wr(self, addr, data):
    if ( self.posted_writes == True and self.ack_state == True ):
      self.ser.write( "E 0\n".encode("utf-8") );
      self.ack_state = False;

    s = "".join(["w %x" % addr] +
                [" %x" % d for d in data] +
                ["\n"])
    self.ser.write(s.encode("utf-8"));
    if ( self.posted_writes == False ):
      rts = self.ser.readline();
      rts = rts.decode("utf-8");
      if '\n' not in rts:
        print("ERROR: bd.wr() : Serial Port Timeout!! " + s + ":" + rts );

  def wr_repeat(self, addr, data):
    if ( self.posted_writes == True and self.ack_state == True ):
      self.ser.write( "E 0\n".encode("utf-8") );
      self.ack_state = False;

    s = "".join(["W %x" % addr] +
                [" %x" % d for d in data] +
                ["\n"])
    self.ser.write(s.encode("utf-8"));
    if ( self.posted_writes == False ):
      rts = self.ser.readline();
      rts = rts.decode("utf-8");
      if '\n' not in rts:
        print("ERROR: bd.wr() : Serial Port Timeout!! " + s + ":" + rts );


  def rd( self, addr, num_dwords=1 ):
    if ( self.posted_writes == True and self.ack_state == False ):
      self.ser.write( "E 8\n".encode("utf-8") );
      rts = self.ser.readline();
      self.ack_state = True;

    s = "r %x %x\n" % (addr, (num_dwords-1)); # Non-RLE Read
    self.ser.write(s.encode("utf-8"));
    rts = self.ser.readline();
    rts = rts.decode("utf-8");
    try:
      rts_conv = [int(rts[8*k:8*(k + 1)], 16) for k in range(num_dwords)]
    except:
      print("ERROR: bd.rd() Serial Port Timeout!!");
      rts_conv = [0xdeaddead];
    return rts_conv;

  def rd_repeat( self, addr, num_dwords=1 ):
    if ( self.posted_writes == True and self.ack_state == False ):
      self.ser.write( "E 8\n".encode("utf-8") );
      rts = self.ser.readline();
      self.ack_state = True;
    # Sump has already subtracted 1 from num_dwords
    s = "k %x %x\n" % (addr, (num_dwords) ); #  Loop Read
    self.ser.write(s.encode("utf-8"));
    rts = self.ser.readline();
    rts = rts.decode("utf-8");
    foo = len( rts );
    try:
      rts_conv = [int(rts[8*k:8*(k + 1)], 16) for k in range(num_dwords+1)]
    except:
      print("ERROR: bd.rd_repeat() Serial Port Timeout!!");
      rts_conv = [0xdeaddead];
    return rts_conv;

  # This sends a locally referenced top.bit binary file to 
  # S3 Hubbard Board FPGA for configuration over Backdoor.
  def configure(self, file_name ):
    print("bd.configure() " + file_name);
    try:
      if ( file_name[-2:] != "gz" ):
        file_in = open ( file_name, 'rb' );# Read in binary top.bit file
        while True:
          packet = file_in.read( 4096 );   # 4K at a time
          if packet:
            self.ser.write( packet );      # send out to serial port
          else:
            break;
        file_in.close();
      else:
        import gzip;
        file_in = open( file_name , 'rb' );
        file_in_gz = gzip.GzipFile( fileobj= file_in,mode='rb' );
        while True:
          packet = file_in_gz.read( 4096 );# 4K at a time
          if packet:
            self.ser.write( packet );      # send out to serial port
          else:
            break;
        file_in_gz.close();
        file_in.close();
      self.ser.flushOutput();
      self.ser.flushInput();
      self.ser.write("!!");
      rts = self.ser.readline();
      print("bd.configure() Complete");
    except:
      print("bd.configure() FAILED!");
    rts = "\n";
    return [rts];

  def close(self):
    if ( self.posted_writes == True and self.ack_state == False ):
      self.ser.write( "E 8\n".encode("utf-8") );
      rts = self.ser.readline();
      self.ack_state = True;
    self.ser.flushOutput();
    self.ser.flushInput();
    self.ser.close()

  def __del__(self):
    try:
      self.ser.close()
    except:
      raise RuntimeError("Backdoor ERROR: Unable to close COM Port!!")

try:
  if __name__=='__main__': main()
except KeyboardInterrupt:
  print('Break!')
# EOF
