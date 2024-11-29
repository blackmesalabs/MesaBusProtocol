/* ****************************************************************************
-- (C) Copyright 2015 Black Mesa Labs
-- Source file: mesa_rx_uart.v                
-- Date:        June 1, 2015   
-- Author:      khubbard
-- Description: A UART that is fixed baud and receive only. This design is a
--              derivative of the autobauding rx+tx mesa_uart.v module.
-- Language:    Verilog-2001 
--
-- RXD    \START/<D0><D1><D2><..><D7>/STOP
--
-- Note: baud_rate[15:0] is actual number of clocks in a symbol:
--       Example 10 Mbps with 100 MHz clock, baud_rate = 0x000a;// Div-10
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   06.01.15  khubbard Creation
-- 0.2   08.18.16  khubbard rx_sr[2:0] fix for metastable sampling issue.
-- ***************************************************************************/
//`default_nettype none // Strictly enforce all nets to be declared
                                                                                
module mesa_rx_uart
(
  input  wire         reset,
  input  wire         clk,
  input  wire         rxd,
  output wire [7:0]   rx_byte,
  output wire         rx_rdy,
  input  wire [15:0]  baud_rate
); // module mesa_rx_uart


  reg  [8:0]    rx_byte_sr;
  reg  [3:0]    rx_bit_cnt;
  reg           sample_now;
  reg           sample_now_p1;
  reg           rxd_meta;
  wire          rxd_sample;
  reg  [7:0]    rxd_sr;
  reg           rx_byte_jk;
  reg           rx_byte_jk_p1;

  wire [7:0]    rx_byte_loc;
  reg  [15:0]   rx_cnt_16b;
  wire [15:0]   baud_rate_loc;
  reg           rx_cnt_16b_p1;
  reg           rx_cnt_16b_roll;
  reg           rx_start_b;
  reg           rx_cnt_en_b;
  reg           rx_rdy_loc;
  reg           rxd_fal;
  reg           rxd_ris;


  assign baud_rate_loc = baud_rate[15:0];
  assign rx_rdy        = rx_rdy_loc;


//-----------------------------------------------------------------------------
// Asynchronous sampling of RXD into 4 bit Shift Register
// Note: RXD is immediately inverted to prevent runt '0's from pipeline 
// being detected as start bits. FPGA Flops powerup to '0', so inverting fixes.
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_din
 begin
   rxd_meta    <= ~ rxd;// Note Inversion to prevent runt post config
   rxd_sr[7:0] <= { rxd_sr[6:0], rxd_meta };
   rxd_fal <= 0;
   rxd_ris <= 0;

// if ( rxd_sr[2:0] == 3'b001 ) begin      
   if ( rxd_sr[2:0] == 3'b011 ) begin      
     rxd_fal <= 1;
   end 
// if ( rxd_sr[2:0] == 3'b110 ) begin      
   if ( rxd_sr[2:0] == 3'b100 ) begin      
     rxd_ris <= 1;
   end 

 end 
end // proc_din
  assign rxd_sample = ~ rxd_sr[2];


//-----------------------------------------------------------------------------
// 16bit Counter used for both rx_start_bit width count and sample count
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_cnt
 begin

  if ( rx_start_b == 1 ) begin
//  rx_cnt_16b <= 16'd0;
    rx_cnt_16b <= 16'd2;// This makes the baud_rate input correct
  end else if ( rx_cnt_en_b == 1 ) begin
    rx_cnt_16b <= rx_cnt_16b + 1;
  end

  rx_cnt_16b_p1    <= rx_cnt_16b[15];
  rx_cnt_16b_roll  <= rx_cnt_16b_p1 & ~ rx_cnt_16b[15];

 end
end // proc_cnt


//-----------------------------------------------------------------------------
// look for falling edge of rx_start_bit and count 1/2 way into bit and sample
//-----------------------------------------------------------------------------
always @ ( posedge clk ) begin : proc_s2 
 begin
  rx_rdy_loc    <= 0;
  rx_start_b    <= 0;
  rx_cnt_en_b   <= 0;
  rx_byte_jk_p1 <= rx_byte_jk;
  sample_now    <= 0;
  sample_now_p1 <= sample_now;

  if ( rx_byte_jk == 0 ) begin
    rx_bit_cnt <= 4'd0;
    if ( rxd_fal == 1 ) begin
      rx_start_b <= 1;
      rx_byte_jk <= 1;// Starting a new Byte
    end
  end

  // assert sample_now at 1/2 baud into D0 data bit.
  if ( rx_byte_jk == 1 ) begin
    rx_cnt_en_b  <= 1;
    if ( rx_bit_cnt == 4'd1 ) begin
      // Div-2 baud count to sample middle of eye
      if ( rx_cnt_16b[15:0] == { 1'b0, baud_rate_loc[15:1] } ) begin
        rx_bit_cnt <= rx_bit_cnt + 1;
        rx_start_b <= 1;
        sample_now <= 1;
      end
    end else if ( rx_cnt_16b[15:0] == baud_rate_loc[15:0] ) begin
      rx_bit_cnt <= rx_bit_cnt + 1;
      rx_start_b <= 1;
      sample_now <= 1;
    end
  end

  if ( sample_now == 1 ) begin
    rx_byte_sr[8]   <= rxd_sample;
    rx_byte_sr[7:0] <= rx_byte_sr[8:1];
  end

  if ( sample_now_p1 == 1 && rx_bit_cnt == 4'd9  ) begin
    rx_byte_jk <= 0;
    rx_bit_cnt <= 4'd0;
  end

  if ( reset == 1 ) begin
    rx_byte_jk <= 0;
    rx_byte_sr[8:0] <= 9'd0;
  end

   // Grab received byte after last bit received
   if ( sample_now_p1  == 1 && rx_bit_cnt == 4'd9 ) begin
     rx_rdy_loc <= 1;
   end

 end
end // proc_s2 
  assign rx_byte_loc = rx_byte_sr[8:1];
  assign rx_byte     = rx_byte_sr[8:1];


endmodule // mesa_rx_uart
