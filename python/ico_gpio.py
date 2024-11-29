##############################################################################
# (C) Copyright 2016 Kevin M. Hubbard, Black Mesa Labs
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# 11.25.2016 : Kevin M. Hubbard created
# 
# Installing spidev for RaspberryPi for SPI communications
#   sudo apt-get install python-dev
#   sudo apt-get install git
#   git clone git://github.com/doceme/py-spidev
#   cd py-spidev
#   sudo python setup.py install
##############################################################################
#import os.path;
#from pygame.locals import *
#import array;
#import random;

import time;
import sys;
import datetime;
from time import sleep;
import spidev;

class App ():
  def __init__(self):
    return;

  def main(self):
    self.main_init();
    self.main_loop();

  def main_init( self ):
    args = sys.argv + [None]*5;# args[0] is this scripts name
    self.dbg_flag = args[1];# ie debug or display or pi etc

    # use SPI for MesaBus instead of UART
    self.spi_port = spidev.SpiDev();
    self.spi_port.open(0,1);# Note: icoboard uses CE0 for Mach, CE1 for Ice
    # Note: SPI rate works up to 32 MHz, but the CS_L time is software 
    # controlled and the gap between 2 byte cycles is always about 300us
    # Low Level SPI Timing
    # 1  MHz : Write = 200uS, Read = 127uS
    # 32 MHz : Write = 20uS, Read = 12uS
    # LocalBus Timing
    # Write : 800uS ( two back to back )
    # Read : 400uS
    self.spi_port.max_speed_hz = 32000000;# 1-32 MHz typical
    self.mb = mesa_bus( self.spi_port);# Establish a MesaBus link
    self.lb = local_bus( self.mb, self.dbg_flag );# Establish a LocalBus link 
    self.define_reg_space();


#   print("Sleeping 5sec to allow for SUMP2 Arm");
#   sleep(5.0);
#   # On PMOD P2, drive a 8bit binary counter to LEDs
#   for i in range( 0,256,1 ):
#     self.lb.wr( self.reg_pmod_p2_ctrl, [ i ] );
#     data = self.lb.rd( self.reg_pmod_p2_ctrl, 1 )[0];
#     sleep(0.02);
#   self.lb.wr( self.reg_pmod_p2_ctrl, [0x55] );
#   print("READ %08X" % data );
#   sys.exit();

    # Read MesaBus ID information from this FPGA
    ( id_mfr, id_dev, id_snum, id_timestamp, english_time ) = self.mesa_id();
    print( id_mfr  );
    print( id_dev  );
    print( id_snum );
    print( id_timestamp );
    print( english_time );

    # Read some registers
    data = self.lb.rd( 0x00000000, 1 )[0];
    print("READ %08X" % data );
    data = self.lb.rd( 0x00000004, 1 )[0];
    print("READ %08X" % data );
    data = self.lb.rd( 0x00000008, 1 )[0];
    print("READ %08X" % data );
 
    # Configure GPIO Pins on the 4 PMOD connectors P1,P2,P3,P4
    # Note: see source/reg_space.txt for bitfield definitions
    self.lb.wr( self.reg_pmod_p1_cfg , [ 0x77777777 ] );# Watch SPI Traffic
#   self.lb.wr( self.reg_pmod_p2_cfg , [ 0x11111111 ] );
#   self.lb.wr( self.reg_pmod_p3_cfg , [ 0x11111111 ] );
#   self.lb.wr( self.reg_pmod_p4_cfg , [ 0x11111111 ] );
#   sys.exit();

#   self.lb.wr( self.reg_pmod_p1_ctrl, [ 0x00000001 ] );
#   self.lb.wr( self.reg_pmod_p2_ctrl, [ 0x00000003 ] );
#   self.lb.wr( self.reg_pmod_p3_ctrl, [ 0x00000007 ] );
#   self.lb.wr( self.reg_pmod_p4_ctrl, [ 0x0000000f ] );

#   self.lb.wr( self.reg_pmod_p1_cfg , [ 0x00000a98 ] );# PWM0,1 and 2
    self.lb.wr( self.reg_pmod_p2_cfg , [ 0xfedcba98 ] );# PWM0,1 and 2
    self.lb.wr( self.reg_pmod_p3_cfg , [ 0xfedcba98 ] );# PWM0,1 and 2
    self.lb.wr( self.reg_pmod_p4_cfg , [ 0xfedcba98 ] );# PWM0,1 and 2
    self.lb.wr( self.reg_pwm0_cfg,     [ 0x01001013 ] );
    self.lb.wr( self.reg_pwm1_cfg,     [ 0x01002013 ] );
    self.lb.wr( self.reg_pwm2_cfg,     [ 0x01004013 ] );
    self.lb.wr( self.reg_pwm3_cfg,     [ 0x01008013 ] );
    self.lb.wr( self.reg_pwm4_cfg,     [ 0x01001023 ] );
    self.lb.wr( self.reg_pwm5_cfg,     [ 0x02001023 ] );
    self.lb.wr( self.reg_pwm6_cfg,     [ 0x04001023 ] );
    self.lb.wr( self.reg_pwm7_cfg,     [ 0x08001023 ] );

    # On PMOD P2, drive a 8bit binary counter to LEDs
#   for i in range( 0,256,1 ):
#     self.lb.wr( self.reg_pmod_p2_ctrl, [ i ] );
#     sleep(0.02);
#   self.lb.wr( self.reg_pmod_p2_ctrl, [0x55] );
    sys.exit();

#   if ( self.platform == "pi" ):
#     import os;
#     os.system("sudo shutdown -h now");

  def main_loop( self ):
    self.test = False; 
    while (True):
      sleep(1);
      print("Looping");
    
  def mesa_id( self ):
    # Issue a low level MesaBus ID Request and make sure FPGA responds
    try:
      self.mb.wr( slot = 0x00, subslot = 0xF, cmd = 0xA, payload = "" );
      rts = self.mb.port.xfer2(20*[0xFF]);
      hex_str = "";
      for each in rts:
        hex_str += ("%02x" % each );
      rts = hex_str;
      if ( len( rts ) == 40 ):
        mesa_header  = rts[0:8];
        id_mfr       = rts[8:16];
        id_dev       = rts[16:24];
        id_snum      = rts[24:32];
        id_time      = rts[32:40];
        english_time = datetime.datetime.fromtimestamp(int( \
                       id_time,16)).strftime('%Y-%m-%d %H:%M:%S');
        return ( id_mfr, id_dev, id_snum, id_time,english_time );
      else:
        return False;
    except:
      return False;

  def define_reg_space(self):
    self.reg_id           = 0x00000000;
    self.reg_version      = 0x00000004;
    self.reg_timestamp    = 0x00000008;
    self.reg_chip_ctrl    = 0x0000000c;
    self.reg_sump2_ctrl   = 0x00000010;
    self.reg_sump2_data   = 0x00000014;
    self.reg_pmod_p1_cfg  = 0x00000020;
    self.reg_pmod_p2_cfg  = 0x00000024;
    self.reg_pmod_p3_cfg  = 0x00000028;
    self.reg_pmod_p4_cfg  = 0x0000002c;
    self.reg_pmod_p1_ctrl = 0x00000030;
    self.reg_pmod_p2_ctrl = 0x00000034;
    self.reg_pmod_p3_ctrl = 0x00000038;
    self.reg_pmod_p4_ctrl = 0x0000003c;
    self.reg_pwm0_cfg     = 0x00000080;
    self.reg_pwm1_cfg     = 0x00000084;
    self.reg_pwm2_cfg     = 0x00000088;
    self.reg_pwm3_cfg     = 0x0000008c;
    self.reg_pwm4_cfg     = 0x00000090;
    self.reg_pwm5_cfg     = 0x00000094;
    self.reg_pwm6_cfg     = 0x00000098;
    self.reg_pwm7_cfg     = 0x0000009c;
    return;

  def quit(self):
    pygame.display.quit();


###############################################################################
# Routines for Reading and Writing a remote 32bit LocalBus over MesaBus
# A local bus cycle is a pre-determined payload transported over the MesaBus
# LocalBus is mapped to SubSlot 0x0
#  0x0 : Write DWORD or Burst starting at Address
#  0x1 : Read  DWORD or Burst starting at Address
#  0x2 : Write Multiple DWORDs to same Address
#  0x3 : Read Multiple DWORDs from same Address
class local_bus:
  def __init__ ( self, mesa_bus, dbg_flag ):
    self.mesa_bus = mesa_bus;
    self.dbg_flag = dbg_flag;

  def wr( self, addr, data ):
    # LocalBus WR cycle is a Addr+Data 8byte payload 
    # Mesabus has maximum payload of 255 bytes, or 63 DWORDs.
    # 1 DWORD is LB Addr, leaving 62 DWORDs available for data bursts
    # if data is more than 62 dwords, parse it into multiple bursts
    each_addr = addr;
    data_list = data;
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
        each_addr +=4;
#     print(payload);
      self.mesa_bus.wr( 0x00, 0x0, 0x0, payload );
    return;

  def rd( self, addr, num_dwords ):
    dwords_remaining = num_dwords;
    each_addr = addr;
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
      self.mesa_bus.wr( 0x00, 0x0, 0x1, payload );
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
#           print("ERROR:Invalid LocalBus Read "+rts_mesa+" "+rts_dword);
            if ( self.dbg_flag == "debug" ):
              sys.exit();
#           rts += [ 0xdeadbeef ];
            rts += [ 0x00000000 ];
      else:
#       print("ERROR: Invalid LocalBus Read " + rts_mesa + " " + rts_dword);
        if ( self.dbg_flag == "debug" ):
          sys.exit();
#       rts += [ 0xdeadbeef ];
        rts += [ 0x00000000 ];
      each_addr += ( 4 * n_dwords );
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
    self.port = port;

  def wr( self, slot, subslot, cmd, payload ):
    preamble  = "FFF0";
    slot      = "%02x" % slot;
    subslot   = "%01x" % subslot;
    cmd       = "%01x" % cmd;
    num_bytes = "%02x" % ( len( payload ) / 2 );
    mesa_str  = preamble + slot + subslot + cmd + num_bytes + payload;
#   print( mesa_str );
    if ( type( self.port ) == spidev.SpiDev ):
      mesa_hex_list = [];
      for i in range( 0, len(mesa_str)/2 ):
        mesa_hex = int(mesa_str[i*2:i*2+2],16);
        mesa_hex_list += [mesa_hex];
#       print("%02x" % mesa_hex );
      rts = self.port.xfer2( mesa_hex_list );
#     print( rts);
    else:
      self.port.wr( mesa_str );
    return;

  def rd( self ):
    if ( type( self.port ) == spidev.SpiDev ):
      hex_str = "";
      rts = self.port.xfer2(8*[0xFF]);
      for each in rts:
        hex_str += ("%02x" % each );
      rts = hex_str;
#     print rts;
    else:
      rts = self.port.rd();
#   print( rts );
    return rts;

###############################################################################
app = App();
app.main();
