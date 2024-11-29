/* ****************************************************************************
-- (C) Copyright 2015 Kevin M. Hubbard @ Black Mesa Labs
-- Source file: mesa2spi.v                
-- Date:        October 4, 2015   
-- Author:      khubbard
-- Language:    Verilog-2001 
-- Description: A Mesa Bus to SPI translator. Uses a Subslot for SPI RDs,WRs.
--
--    "\n"..."FFFF"."(F0-12-34-04)[11223344]\n" : 
--        0xFF = Bus Idle ( NULLs )
--  B0    0xF0 = New Bus Cycle to begin ( Nibble and bit orientation )
--  B1    0x12 = Slot Number, 0xFF = Broadcast all slots, 0xFE = NULL Dest
--  B2    0x3  = Sub-Slot within the chip (0-0xF)
--        0x4  = Command Nibble for Sub-Slot
--  B3    0x04 = Number of Payload Bytes (0-255) : Length of SPI Cycle
--        0x11223344 = Payload
--
--    Sub-Slot Commands
--       0x0 = SPI Write Burst from Mesa to SPI with SPI faster than Mesa
--       0x1 = SPI Cycle : Byte and Continue ( for SPI slower than Mesa )
--       0x2 = SPI Cycle : Last Byte ( deasserts SS after xfer )
--
-- Fast Mode: single LF at end of SPI Cycle
--   Burst        : 0x0
--
-- Slow Mode: LF at end of each byte
--   Single Byte  : 0x2
--   Two Bytes    : 0x1,0x2
--   Three+ Bytes : 0x1,0x1,..0x2
-- 
--
-- Example MesaBus Cycle with 2-Byte Payload:
--   rx_byte_start _/  \___________________________________________
--   rx_byte_rdy   _/  \____/  \____/  \____/  \____/  \____/  \___
--   rx_byte_d     -<F0>----<00>----<00>----<02>----<11>----<22>---
--   rx_byte_stop  _________________________________________/  \__
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   10.04.15  khubbard Creation
-- ***************************************************************************/
`default_nettype none // Strictly enforce all nets to be declared
                                                                                
module mesa2spi
(
  input  wire         clk,
  input  wire         reset,
  input  wire [3:0]   subslot,
  input  wire         rx_byte_start,
  input  wire         rx_byte_stop,
  input  wire         rx_byte_rdy,
  input  wire [7:0]   rx_byte_d,
  output reg  [7:0]   tx_byte_d,
  output reg          tx_byte_rdy,
  output reg          tx_done,
  input  wire         tx_busy,

  input  wire [3:0]   spi_ck_div,
  output reg          spi_sck,
  input  wire         spi_miso,
  output reg          spi_mosi,
  output reg          spi_ss_l

); // module mesa2spi


  reg [3:0]     byte_cnt;
  reg [31:0]    dword_sr;
  reg           rx_byte_rdy_p1;
  reg           rx_byte_rdy_p2;
  reg           rx_byte_rdy_p3;
  reg           rx_byte_stop_p1;
  reg           rx_byte_stop_p2;
  reg           rx_byte_stop_p3;
  reg           spi_ck_loc;
  reg           spi_cycle_jk;
  reg [4:0]     spi_halfbit_cnt;
  reg [3:0]     spi_ck_cnt;
  reg [7:0]     spi_mosi_sr;
  reg [7:0]     spi_miso_sr;
  reg           spi_miso_loc;
  reg           dword_rdy;
  reg           header_jk;
  reg           spi_mosi_loc;
  reg           spi_ss_loc;
  reg           sample_miso;
  reg           sample_miso_p1;
  reg           sample_miso_p2;
  reg [1:0]     mesa_cmd;


//-----------------------------------------------------------------------------
// Convert a MesaBus payload into SPI bus cycles
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_lb1
 rx_byte_rdy_p1  <= rx_byte_rdy;
 rx_byte_rdy_p2  <= rx_byte_rdy_p1;
 rx_byte_rdy_p3  <= rx_byte_rdy_p2;
 rx_byte_stop_p1 <= rx_byte_stop;
 rx_byte_stop_p2 <= rx_byte_stop_p1;
 rx_byte_stop_p3 <= rx_byte_stop_p2;
 dword_rdy       <= 0;

 if ( rx_byte_start == 1 ) begin
   byte_cnt     <= 4'd0;
   header_jk    <= 1;
 end else if ( rx_byte_rdy == 1 ) begin 
   if ( byte_cnt[3:0] != 4'd4 ) begin
     byte_cnt <= byte_cnt + 1; 
   end
 end 

 // Shift bytes into a 32bit SR
 if ( rx_byte_rdy == 1 ) begin 
   dword_sr[31:0] <= { dword_sr[23:0], rx_byte_d[7:0] };
 end

 // After we have 4 bytes, look for Slot=00,SubSlot=n,Command=m 
 if ( rx_byte_rdy_p2 == 1 && byte_cnt[1:0] == 2'd3 ) begin
   header_jk <= 0;
   dword_rdy <= 1;
   // Note: This doesn't handle slot broadcast - only direct for LB Access
   if ( header_jk == 1 && dword_sr[31:16] == 16'hF000 ) begin
     if ( dword_sr[15:12] == subslot[3:0] ) begin
       spi_cycle_jk  <= 1;
       mesa_cmd[1:0] <= dword_sr[9:8];
     end
   end 
 end // if ( rx_byte_rdy_p2 == 1 && byte_cnt[1:0] == 2'd3 ) begin

 if ( rx_byte_stop_p3 == 1 ) begin
   header_jk    <= 0;
   if ( mesa_cmd == 2'd0 || mesa_cmd == 2'd2 ) begin
     spi_cycle_jk <= 0;
   end
 end
 if ( reset == 1 ) begin
   spi_cycle_jk <= 0;
   header_jk    <= 0;
 end
 
end // proc_lb1


//-----------------------------------------------------------------------------
// Convert incoming bytes into SPI bytes at specified clock divisor rate
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_lb2
 sample_miso    <= 0;
 sample_miso_p1 <= sample_miso;
 sample_miso_p2 <= sample_miso_p1;
 tx_byte_rdy    <= 0;
 tx_done        <= 0;
 if ( rx_byte_rdy == 1 && spi_cycle_jk == 1 && byte_cnt[3:0] == 4'd3 ) begin
   spi_mosi_sr     <= rx_byte_d[7:0];
   spi_halfbit_cnt <= 5'd16;
   spi_ck_cnt      <= 4'd0;
   spi_ck_loc      <= 1;
   spi_ss_loc      <= 1;
   spi_ck_cnt      <= spi_ck_div[3:0];
 end else if ( spi_halfbit_cnt != 5'd0 ) begin
   // actions happen when clock half period counter reaches 0
   if ( spi_ck_cnt == spi_ck_div[3:0] ) begin
     spi_halfbit_cnt <= spi_halfbit_cnt - 1;
     spi_ck_cnt      <= 4'd0;
     spi_ck_loc      <= ~spi_ck_loc;
     // Shift new data out on falling clock edge
     if ( spi_ck_loc == 1 ) begin
       spi_mosi_sr  <= { spi_mosi_sr[6:0], 1'b1 };
       spi_mosi_loc <= spi_mosi_sr[7];
     end
     sample_miso <= ~ spi_ck_loc;
   end else begin
     spi_ck_cnt <= spi_ck_cnt[3:0] + 1;
   end 
 end else begin
   spi_halfbit_cnt <= 5'd0;
   spi_ck_loc      <= 1;
   spi_mosi_loc    <= 1;
   if ( spi_cycle_jk == 0 ) begin
     spi_ss_loc <= 0;
   end
 end
 if ( sample_miso_p1 == 1 ) begin
   spi_miso_sr  <= { spi_miso_sr[6:0], spi_miso_loc };
// spi_miso_sr  <= { spi_miso_sr[6:0], spi_mosi_loc };// Just for sims
 end
 if ( sample_miso_p2 == 1 && spi_halfbit_cnt == 5'd0 ) begin
  tx_byte_d   <= spi_miso_sr[7:0];
  tx_byte_rdy <= 1;
  if ( spi_cycle_jk == 0 ||
       mesa_cmd == 2'd1     ) begin
    tx_done <= 1;// Queue up a \n LF
  end
 end

 spi_ss_l     <= ~ spi_ss_loc;
 spi_sck      <= spi_ck_loc;
 spi_mosi     <= spi_mosi_loc;
 spi_miso_loc <= spi_miso;

end // proc_lb2


endmodule // mesa2spi
