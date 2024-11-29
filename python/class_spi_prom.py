#!python3
###############################################################################
# Source file : class_spi_prom.py
# Language    : Python 3.7
# Author      : Kevin Hubbard
# Description : Access SPI PROM via MesaBus and spi_prom.v
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
from common_functions import file2list;
from common_functions import list2file;


###############################################################################
# Software Interface layer to spi_prom.v. This IP block is two registers, a
# control register and a data streaming register that connects to a small FSM
# and Block RAM for writing 256 bytes at a time to a SPI PROM.
# These spi_* functions interface via Backdoor to 2 LocalBus mapped registers
# connected to spi_prom.v that then interfaces via SPI to a SPI PROM.
# Interface is a 32bit LB Command Register and a 32bit LB Streaming Data Reg
class spi_prom:
  def __init__ ( self, lb_link ):
    self.bd = lb_link;
    # These are some constants from spi_prom.v
    self.prom_stat_spi_busy          = 0x80;
    self.prom_stat_mosi_polling_reqd = 0x40;
    self.prom_stat_mosi_rdy          = 0x20;
    self.prom_stat_miso_rdy          = 0x10;
    self.prom_stat_state_wr          = 0x08;
    self.prom_stat_unlocked          = 0x04;
    self.prom_stat_prom_wip          = 0x02;
    self.prom_stat_spi_busy          = 0x01;
    self.prom_cmd_erase_bulk         = 0x05;
    self.prom_cmd_erase_sector       = 0x06;
    self.prom_cmd_wr_prom            = 0x07;
    self.prom_cmd_boot               = 0x08;
    self.prom_cmd_rd_prom            = 0x03;
    self.prom_cmd_rd_timestamp       = 0x02;
    self.prom_cmd_id                 = 0x01;
    self.prom_cmd_root               = 0x05aaa504;
    self.prom_cmd_boot_unlock        = 0x055a5504;
    self.prom_cmd_wr_enable          = 0x0aa5aa04;
    self.prom_cmd_wr_disable         = 0x00000004;
    self.prom_ctrl_addr              = 0x20;
    self.prom_data_addr              = self.prom_ctrl_addr + 0x04;
    self.prom_id_list  = ( (0x01,"Spansion"), \
                           (0x20,"Micron"),   \
                           (0xC2,"Macronix"), \
                         );
    self.cmd_list= ["prom_dump","prom_load","prom_root","prom_boot","prom_id"];
    self.help = [];
    h = self.help;
    h+=["# PROM Access commands                                                                 "];
    h+=["#  prom_root             : Unlock slot-0 if locked                                     "];
    h+=["#  prom_boot addr        : Reboot FPGA from PROM addr                                  "];
    h+=["#  prom_dump addr        : Dump sector at addr                                         "];
    h+=["#  prom_load file addr   : Load PROM from top.bin file to addr                         "];
    h+=["#                          Note: addr may also be slot0 or slot1                       "];

  def proc_cmd( self, cmd_txt, cmd_str ):
    if ( cmd_txt == "prom_dump" ): return self.cmd_prom_dump( cmd_str );
    if ( cmd_txt == "prom_load" ): return self.cmd_prom_load( cmd_str );
    if ( cmd_txt == "prom_root" ): return self.cmd_prom_root( cmd_str );
    if ( cmd_txt == "prom_boot" ): return self.cmd_prom_boot( cmd_str );
    if ( cmd_txt == "prom_id"   ): return self.cmd_prom_id(   cmd_str );

  def cmd_prom_id( self, cmd_str ):
    try:
      rts = [];
      (vendor_id, prom_size_mb ) = self.prom_id();
      timestamp = self.prom_timestamp();
      slot_size = self.prom_slotsize();
      import time;
      means = time.ctime(timestamp)

      rts += [ ("Manufacturer: %s" % vendor_id    ) ];
      rts += [ ("Size: %d Mb"      % prom_size_mb ) ];
      rts += [ ("Slot_Size: %08x"  % slot_size    ) ];
      rts += [ ("Timestamp: %08x : %s " % (timestamp,means) ) ];
    except:
      rts = ["ERROR: cmd_prom_id() unable to communicate with Hardware"]; 
    return rts;

  def cmd_prom_boot( self, cmd_str ):
    words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
    addr = int(words[1],16);
    try:
      rts = self.prom_boot( addr );
    except:
      rts = ["ERROR: cmd_prom_boot() unable to communicate with Hardware"]; 
    return rts;

  def cmd_prom_dump( self, cmd_str ):
    try:
      words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
      addr = int(words[1],16);
      rts = self.prom_dump( addr = addr );
      txt_rts = [ "%08x" % each for each in rts ];# list comprehension
    except:
      txt_rts = ["ERROR: cmd_prom_dump() unable to communicate with Hardware"]; 
    return txt_rts;

  # "prom_load top.bin slot1" or "prom_load top.bin 00200000"
  def cmd_prom_load( self, cmd_str ):
    try:
      words = " ".join(cmd_str.split()).split(' ') + [None] * 4;
      if ( words[2][0:4] == "slot" ):
        slot_size = self.prom_slotsize();
        addr = slot_size * int(words[2][4], 10 );
      else:
        addr = int( words[2], 16 );
      bitstream = file2list( words[1], binary = True );
      print("Loading %s to address %08x" % ( words[1], addr ) );
      rts = self.prom_load( addr, bitstream );
    except:
      rts = ["ERROR: cmd_prom_load() unable to communicate with Hardware"]; 
    return rts;

  def cmd_prom_root( self, cmd_str ):
    try:
      rts = self.prom_root();
    except:
      rts = ["ERROR: cmd_prom_root() unable to communicate with Hardware"]; 
    return rts;


  def prom_id( self ):
    self.spi_tx_ctrl( self.prom_cmd_id );
    rts = self.spi_rx_data( 1 );
    vendor_id = "unknown";
    for ( id_hex, id_str ) in self.prom_id_list:
      if ( id_hex == ( rts[0] & 0x000000FF ) ):
        vendor_id = id_str;
    prom_size_mb = 2**((rts[0] & 0x00FF0000)>>16)/131072;
    return ( vendor_id, prom_size_mb );

  def prom_timestamp( self ):
    self.spi_tx_ctrl( self.prom_cmd_rd_timestamp );
    rts = self.spi_rx_data( num_dwords = 2 );
    return rts[0];

  def prom_slotsize( self ):
    self.spi_tx_ctrl( self.prom_cmd_rd_timestamp );
    rts = self.spi_rx_data( num_dwords = 2 );
    return rts[1];

  def prom_root( self ):
    self.spi_tx_ctrl( self.prom_cmd_root );
    return;

  def prom_boot( self, addr ):
    dword = self.prom_cmd_boot_unlock;
    self.spi_tx_ctrl( dword ); 
    dword = (addr & 0xFFFFFF00 ) | self.prom_cmd_boot;
    self.spi_tx_ctrl( dword ); 
    return;

  def prom_erase( self, addr ):
    dword = (addr & 0xFFFFFF00 ) | self.prom_cmd_erase_sector;
    self.spi_tx_ctrl( dword );# Address+Sector Erase Command
    bit_status = self.prom_stat_prom_wip; i = 0;
    while ( bit_status == self.prom_stat_prom_wip and i < 1000 ):
      rts = self.bd.rd( self.prom_ctrl_addr,1 )[0];
      bit_status = rts & self.prom_stat_prom_wip; 
      i +=1;
    return;

  def prom_dump( self, addr ):
    dword = (addr & 0xFFFFFF00 ) | self.prom_cmd_rd_prom;
    self.spi_tx_ctrl( dword );# Address+Sector Read Command
    rts = self.spi_rx_data( num_dwords = 64 );# 64 DWORDs = 256 Bytes
    return rts;

  def prom_load( self, addr, data_byte_list ):
    import time;
    t0 = time.time();

    self.spi_tx_ctrl( self.prom_cmd_wr_enable );# Unlock for Writing
    # A sector is 64K, or 256 pages of 256 bytes.
    page_cnt = 0;
    bytes_remaining = len( data_byte_list );
    bits_total = bytes_remaining * 8;
    while( bytes_remaining > 0 ):
      if ( page_cnt == 0 ):
        print("Erasing sector at %08x" % addr );
        t1 = time.time();
        self.prom_erase( addr );# Erase this sector
#       t2 = time.time();
#       print("  %d Seconds" % ( t2-t1 ) );
        print("Writing sector");
        dword = ( addr & 0xFFFFFF00 ) | self.prom_cmd_wr_prom;
        self.spi_tx_ctrl( dword );# Write Command
      page_cnt += 1;
      if ( page_cnt == 256 ):
        page_cnt = 0;
        t3 = time.time();
        print("  %d Seconds" % ( t3-t1 ) );

      # Extract 256 bytes from entire byte list
      if ( bytes_remaining > 256 ):
        write_bytes = data_byte_list[0:256];
      else:
        write_bytes = (data_byte_list + [0x00]*256)[0:256];# Pad 00s 
      data_byte_list = data_byte_list[256:];
      data_dword_list = [];
      for i in range (0,64):
        dword = 0;
        for j in range (0,4,+1):
          dword = dword << 8;
          dword = dword | write_bytes[(i*4)+j];
        data_dword_list += [ dword ];
      # Send payload if the MOSI Buffer is Free
      self.spi_wait_for_mosi_free();
      self.spi_tx_data( data_dword_list );
      addr += 256;
      bytes_remaining = len( data_byte_list );
      self.spi_wait_for_mosi_free();
    self.spi_tx_ctrl( self.prom_cmd_wr_disable );# lock back up
    t4 = time.time();
    bits_total = int( bits_total / ( 1024 * 1024 ));
    print("  %d Seconds for %d Mbits" % ( ( t4-t0 ), bits_total ) );
    return;
  
  def spi_tx_ctrl( self, byte_cmd ):
    # Sit in a loop until SPI_BUSY is cleared
    bit_status = 0x1; i = 0;
    while ( bit_status == 0x1 and i < 1000 ):
      rts = self.bd.rd( self.prom_ctrl_addr,1 )[0];
      bit_status = rts & self.prom_stat_spi_busy; # SPI_BUSY Bit
      i +=1;
    if ( i == 1000 ):
      print("ERROR: spi_tx_ctrl() Timeout Abort"); 
#   print("w %08x %08x" % ( self.prom_ctrl_addr, byte_cmd ) );
    self.bd.wr( self.prom_ctrl_addr, [ byte_cmd ] );
    return;

  def spi_wait_for_mosi_free( self ):
    bit_status = 0x0; i = 0;
    while ( bit_status == 0x0 and i < 1000 ):
      rts = self.bd.rd( self.prom_ctrl_addr,1 )[0];
      bit_status = rts & self.prom_stat_mosi_rdy; # 
      i +=1;
    if ( i == 1000 ):
      print("ERROR: spi_tx_ctrl() Timeout Abort"); 
    return;

  def spi_tx_data( self, data_payload ):
    self.bd.wr_repeat( addr=self.prom_data_addr, data_list=data_payload );
    return;

  def spi_rx_data( self, num_dwords ):
    rts = self.bd.rd_repeat( addr=self.prom_data_addr, num_dwords=num_dwords );
    return rts;
