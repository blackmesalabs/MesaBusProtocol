/* ****************************************************************************
-- (C) Copyright 2015 Kevin M. Hubbard @ Black Mesa Labs
-- Source file: mesa_pi_spi.v                
-- Date:        August 2, 2015  
-- Author:      khubbard
-- Description: Convert SPI MOSI stream from a RaspPi to Mesa binary nibbles
-- Language:    Verilog-2001 
-- License:     This project is licensed with the CERN Open Hardware Licence
--              v1.2.  You may redistribute and modify this project under the
--              terms of the CERN OHL v.1.2. (http://ohwr.org/cernohl).
--              This project is distributed WITHOUT ANY EXPRESS OR IMPLIED
--              WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY
--              AND FITNESS FOR A PARTICULAR PURPOSE. Please see the CERN OHL
--              v.1.2 for applicable Conditions.
--
-- 2 MHz Capture
-- pi_spi_cs_l    \________________________________________________________/
-- pi_spi_sck     ___________/  \__/  \__/  \__/  \______/ \_/ \_/ \________ 
-- pi_spi_mosi    ---------< 7  ><  6 >< .. ><  0 >----< 7 ><..><0 >--------
-- pi_spi_miso
--                |<-10us->|                                       |<-2us->|
--
-- http://www.raspberry-projects.com/pi/programming-in-c/spi/
--       using-the-spi-interface
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   08.02.15  khubbard Creation
-- ***************************************************************************/
//`default_nettype none // Strictly enforce all nets to be declared
                                                                                
module mesa_pi_spi
(
  input  wire         pi_spi_sck,
  input  wire         pi_spi_cs_l,
  input  wire         pi_spi_mosi,
  output wire         pi_spi_miso,

  input  wire         mesa_id_req,
  input  wire [31:0]  id_mfr,
  input  wire [31:0]  id_dev,
  input  wire [31:0]  id_snum,
  input  wire [31:0]  id_timestamp,

  input  wire         clk,
  input  wire         lb_rd,
  input  wire [31:0]  lb_rd_d,
  input  wire         lb_rd_rdy,

  output reg  [3:0]   mosi_nib_d,
  output reg  [3:0]   tp_dbg,
  output reg          mosi_nib_rdy
); // module mesa_pi_spi


  reg [1:0]     bit_cnt;
  reg [7:0]     id_bit_cnt;
  reg [3:0]     nib_sr;
  reg [7:0]     miso_byte;
  reg           bit_togl;
  reg           rdy_loc;
  reg           rdy_meta;
  reg           rdy_p1;
  reg           rdy_p2;
  reg           cs_l_meta;
  reg           cs_l_p1;
  reg           cs_l_p2;
  reg           cs_l_p3;
  reg [2:0]     spi_bit_cnt;
  reg [31:0]    rd_d_xfer;
  reg [63:0]    miso_sr;
  reg           lb_rd_rdy_p1;
  reg           rd_rdy_xfer;
  reg           rd_rdy_xfer_wide;
  reg           miso_shift_en;
  reg           mesa_id_jk;


//-----------------------------------------------------------------------------
// Xfer clock domains
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_xfer
 begin
   rdy_meta <= rdy_loc;
   rdy_p1   <= rdy_meta;
   rdy_p2   <= rdy_p1;
   mosi_nib_rdy <= rdy_p1 & ~ rdy_p2;
 end
end


//-----------------------------------------------------------------------------
// Convert MOSI to 2 nibbles to insert in regular UART nibble stream
//  input  pi_spi_sck;
//  input  pi_spi_cs_l;
//  input  pi_spi_mosi;
//  output pi_spi_miso;
//-----------------------------------------------------------------------------
always @ ( posedge pi_spi_sck or posedge pi_spi_cs_l ) begin : proc_tx
 begin
   if ( pi_spi_cs_l == 1 ) begin
     bit_cnt    <= 2'd0;
     rdy_loc    <= 0;
     tp_dbg[3]  <= 0; 
   end else begin
     tp_dbg[3] <= rdy_loc;
     rdy_loc <= 0;
     nib_sr  <= { nib_sr[2:0], pi_spi_mosi };
     bit_cnt <= bit_cnt + 1;
     if ( bit_cnt == 2'd3 ) begin
       mosi_nib_d <= { nib_sr[2:0], pi_spi_mosi };
       rdy_loc    <= 1;
     end
   end
 end
end // proc_tx 


//-----------------------------------------------------------------------------
// Handle the Readback. When 32bit read comes in, latch and then decrement a
// count after each SPI cycle ( where each cycle reads 1 of 8 bytes ).
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_lb_sr
 begin
   cs_l_meta <= pi_spi_cs_l;
   cs_l_p1   <= cs_l_meta;
   cs_l_p2   <= cs_l_p1;
   cs_l_p3   <= cs_l_p2;


   if ( lb_rd_rdy == 1 ) begin
     rd_d_xfer     <= lb_rd_d[31:0];
     miso_shift_en <= 0;// Prevent shift of 1st Ro bit from end of Wi cycle
     mesa_id_jk    <= 0;
   end

   if ( mesa_id_req == 1 ) begin
     miso_shift_en <= 0;// Prevent shift of 1st Ro bit from end of Wi cycle
     mesa_id_jk    <= 1;
   end

   if ( cs_l_p1 == 1 && cs_l_p2 == 0 ) begin
     miso_shift_en <= 1;
   end

   lb_rd_rdy_p1      <= lb_rd_rdy | mesa_id_req;
   rd_rdy_xfer       <= lb_rd_rdy_p1;
   rd_rdy_xfer_wide  <= rd_rdy_xfer | lb_rd_rdy_p1;
   tp_dbg[0]         <= rd_rdy_xfer_wide;

 end
end

//-----------------------------------------------------------------------------
// Reads are handled by MOSI shifting bytes at a time, looking for 0xF0.
// When 0xF0 is received, it then reads 3+4 bytes. 
// Burst reads are NOT supported.
//      0xFF = Bus Idle ( NULLs )                                               
//  B0  0xF0 = New Bus Cycle to begin ( Nibble and bit orientation )            
//  B1  0xFE = Slot Number - Default is 0xFE for Ro traffic                     
//  B2  0x0  = Sub-Slot within the chip (0-0xF)                                 
//      0x0  = Command Nibble for Sub-Slot                                      
//  B3  0x04 = Number of Payload Bytes (0-255)     
//                 Wi Cycle                 Ro Cycle
// spi_cs_l   \________________/        \_____________/
// spi_sck       /\/\/\/\/\________________/\/\/\/\/
//-----------------------------------------------------------------------------
//always @ ( negedge pi_spi_sck or posedge rd_rdy_xfer ) begin : proc_rd_cnt
//if ( rd_rdy_xfer == 1 ) begin
always @ (negedge pi_spi_sck or posedge rd_rdy_xfer_wide) begin : proc_rd_cnt
  tp_dbg[1] <= 0;
  if ( rd_rdy_xfer_wide == 1 ) begin
    miso_sr <= { 32'hF0FE0004, rd_d_xfer[31:0] };
    id_bit_cnt <= 8'd1;
    bit_togl   <= 1'b1;
  end else begin
    if ( pi_spi_cs_l == 0 && miso_shift_en == 1 ) begin
      id_bit_cnt <= id_bit_cnt + 1;
      miso_sr <= { miso_sr[62:0], 1'b1 };
//    miso_sr <= { miso_sr[62:0], bit_togl };// Debug Only 
      bit_togl <= ~ bit_togl;
      if ( id_bit_cnt == 8'd1 ) begin
        tp_dbg[1] <= 1;
      end
      tp_dbg[2] <= bit_togl;
      
      if ( mesa_id_jk == 1 ) begin
        if ( id_bit_cnt == 8'd24 ) begin
          miso_sr[63:56] <= 8'h10;// 16 Bytes or 4 DWORDs
        end
        if ( id_bit_cnt == 8'd32 ) begin
          miso_sr[63:32] <= id_mfr[31:0];
        end
        if ( id_bit_cnt == 8'd64 ) begin
          miso_sr[63:32] <= id_dev[31:0];
        end
        if ( id_bit_cnt == 8'd96 ) begin
          miso_sr[63:32] <= id_snum[31:0];
        end
        if ( id_bit_cnt == 8'd128 ) begin
          miso_sr[63:32] <= id_timestamp[31:0];
        end
      end
    end
  end
end
  assign pi_spi_miso = miso_sr[63];

endmodule // mesa_pi_spi
