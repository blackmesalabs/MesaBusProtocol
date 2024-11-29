/* ****************************************************************************
-- (C) Copyright 2024 Kevin Hubbard - All rights reserved.
-- Source file: top.v                
-- Date:        November 29, 2024
-- Author:      khubbard
-- Description: Artix7 sample design of Mesa Bus over FTDI UART.
-- Language:    Verilog-2001
-- Simulation:  Mentor-Modelsim 
-- Synthesis:   Xilinx-Vivado
-- License:     This project is licensed with the CERN Open Hardware Licence
--              v1.2.  You may redistribute and modify this project under the
--              terms of the CERN OHL v.1.2. (http://ohwr.org/cernohl).
--              This project is distributed WITHOUT ANY EXPRESS OR IMPLIED
--              WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY
--              AND FITNESS FOR A PARTICULAR PURPOSE. Please see the CERN OHL
--              v.1.2 for applicable Conditions.
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   11.29.24  khubbard Creation
-- ***************************************************************************/
`timescale 1 ns/ 100 ps
`default_nettype none // Strictly enforce all nets to be declared

module top 
(
  input  wire         clk,   
  input  wire         bd_rx,     
  output wire         bd_tx,
  input  wire [7:0]   sw,  
  output reg  [7:0]   led
);// module top

  reg           reset_loc = 1;
  wire          clk_100m_loc;
  wire          clk_100m_tree;
  wire          lb_wr;
  wire          lb_rd;
  wire [31:0]   lb_addr;
  wire [31:0]   lb_wr_d;
  reg  [31:0]   lb_rd_d;
  reg           lb_rd_rdy;
  wire          ftdi_wi;
  wire          ftdi_ro;
  reg  [31:0]   reg_04 = 32'd0;

  assign clk_100m_loc = clk; // infer IBUF

  BUFGCE u0_bufg ( .I( clk_100m_loc ), .O( clk_100m_tree ), .CE(1) );

  assign ftdi_wi     = bd_rx;
  assign bd_tx       = ftdi_ro;


//-----------------------------------------------------------------------------
// Configuration reset
//-----------------------------------------------------------------------------
always @ ( posedge clk_100m_tree ) begin : proc_reset
  reset_loc <= 0;
end


//-----------------------------------------------------------------------------
// Local Bus test registers
//-----------------------------------------------------------------------------
always @ ( posedge clk_100m_tree ) begin : proc_bus_regs  
  lb_rd_rdy <= 0;
  lb_rd_d   <= 32'd0;
  led       <= reg_04[7:0];
  if ( lb_rd == 1 ) begin
    lb_rd_rdy <= 1;
    case( lb_addr[7:0] )
      8'h00   : lb_rd_d <= 32'h12345678;
      8'h04   : lb_rd_d <= reg_04[31:0];
      8'h08   : lb_rd_d <= { 24'd0, sw[7:0] };
      default : lb_rd_d <= 32'hDEADBEEF;
    endcase
  end
  if ( lb_wr == 1 ) begin
    case( lb_addr[7:0] )
      8'h00   : begin end
      8'h04   : reg_04  <= lb_wr_d[31:0];
      8'h08   : begin end
      default : begin end
    endcase
  end
end // proc_led_flops


//-----------------------------------------------------------------------------
// MesaBus interface to LocalBus : 2-wire FTDI UART to 32bit PCIe like localbus
// Files available at https://github.com/blackmesalabs/MesaBusProtocol
//   ft232_xface.v, mesa_uart_phy.v, mesa_decode.v, mesa2lb.v, mesa_id.v,
//   mesa2ctrl.v, mesa_uart.v, mesa_tx_uart.v, mesa_ascii2nibble.v, 
//   mesa_byte2ascii.v, iob_bidi.v
//-----------------------------------------------------------------------------
ft232_xface u_ft232_xface
(
  .reset       ( reset_loc       ),
  .clk_lb      ( clk_100m_tree   ),
  .ftdi_wi     ( ftdi_wi         ),
  .ftdi_ro     ( ftdi_ro         ),
  .lb_wr       ( lb_wr           ),
  .lb_rd       ( lb_rd           ),
  .lb_addr     ( lb_addr[31:0]   ),
  .lb_wr_d     ( lb_wr_d[31:0]   ),
  .lb_rd_d     ( lb_rd_d[31:0]   ),
  .lb_rd_rdy   ( lb_rd_rdy       )
);// u_ft232_xface


endmodule // top.v
`default_nettype wire // enable Verilog default for any 3rd party IP needing it
