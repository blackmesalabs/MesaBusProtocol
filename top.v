/* ****************************************************************************
-- Source file: top.v                
-- Date:        November 22, 2016
-- Author:      khubbard
-- Description: Top Level Verilog RTL for Lattice iCE40HX8K-CT256 icoBoard
-- Language:    Verilog-2001 and VHDL-1993
-- Simulation:  Mentor-Modelsim 
-- Synthesis:   Lattice     
-- License:     This project is licensed with the CERN Open Hardware Licence
--              v1.2.  You may redistribute and modify this project under the
--              terms of the CERN OHL v.1.2. (http://ohwr.org/cernohl).
--              This project is distributed WITHOUT ANY EXPRESS OR IMPLIED
--              WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY
--              AND FITNESS FOR A PARTICULAR PURPOSE. Please see the CERN OHL
--              v.1.2 for applicable Conditions.
-- 
--  Top View : Lattice icoBoard atop Pi
--        -----------------------------------------  
--       | ----------------------------------      |
--       ||  [ PMOD P2 ]         [ PMOD P1 ] |  -----
--       ||                                  | | USB |
--       ||                                  |  -----     
--       | \           -----------           |  ----- 
--       |  |         |  Lattice  |          | | USB |
--       |  |         | iCE40HX8K |          |  ----- 
--       | /           -----------           |  -----
--       ||                                  | |Ether|
--       ||                                  | |     |
--       ||  [ PMOD P3 ]         [ PMOD P4 ] |  -----
--       | ----------------------------------      |
--        ----------------------------------------- 
--
--  Side View : Looking into Female PMOD Connector
--          ----------------------------           -------------
--         | 3V GND D[7] D[5] D[3] D[1] |         | 3V GND D[7] ..
--         | 3V GND D[6] D[4] D[2] D[0] |         | 3V GND D[6] ..
--      --------------------------------------------------------
--     |          icoBoard FR4              
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   11.22.16  khubbard Creation
-- ***************************************************************************/
`default_nettype none // Strictly enforce all nets to be declared

module top
(
  input  wire         clk_100m,
  input  wire         sw0,
  input  wire         sw1,
  output wire         led1,    
  output wire         led2,    
  output wire         led3,
  inout  wire [31:0]  gpio_pin,
//inout  wire [7:0]   pmod_p1_d,
//inout  wire [7:0]   pmod_p2_d,
//inout  wire [7:0]   pmod_p3_d,
//inout  wire [7:0]   pmod_p4_d,
  input  wire [7:0]   rpi_gpio,
  input  wire         rpi_spi_ce1_l,
  input  wire         rpi_spi_clk,
  input  wire         rpi_spi_mosi,
  output wire         rpi_spi_miso 
);// module top

  wire          clk_100m_tree;
//wire          clk_100m_loc;
//wire          pll_100m_lock;

  wire [3:0]    mesa_wi_nib_d;
  wire          mesa_wi_nib_en;
  wire [8:0]    subslot_ctrl;
  reg           mesa_id_req;
  wire          lb_wr;
  wire          lb_rd;
  wire [31:0]   lb_addr;
  wire [31:0]   lb_wr_d;
  wire [31:0]   lb_rd_d;
  wire          lb_rd_rdy;
  wire [31:0]   time_stamp_d;
  wire          pi_spi_sck;
  wire          pi_spi_cs_l;
  wire          pi_spi_mosi;
  wire          pi_spi_miso;
  wire [3:0]    pi_mosi_d;
  wire          pi_mosi_rdy;
  reg  [31:0]   test_cnt;
  reg  [31:0]   test_reg;
  wire [7:0]    tp_dbg;
  wire [3:0]    tp_spi_dbg;
  wire [3:0]    led_bus;
  wire [31:0]   dbg_pin;
  reg           lb_wr_p1;
  reg           lb_rd_p1;
  reg           lb_rd_rdy_p1;
  reg           lb_wr_wide;
  reg           lb_rd_wide;
  reg           lb_rd_rdy_wide;

//assign led1 = test_cnt[27];
//assign led2 = test_cnt[26];
  assign led1 = led_bus[1];
  assign led2 = led_bus[0];
  assign led3 = test_cnt[25];// Red

  assign pi_spi_cs_l  = rpi_spi_ce1_l;
  assign pi_spi_sck   = rpi_spi_clk;
  assign pi_spi_mosi  = rpi_spi_mosi;
  assign rpi_spi_miso = pi_spi_miso;

// These signals can be muxed out to a PMOD connector for debug
  assign tp_dbg[0] = rpi_spi_clk;
  assign tp_dbg[1] = rpi_spi_ce1_l;
  assign tp_dbg[2] = rpi_spi_mosi;
  assign tp_dbg[3] = pi_spi_miso;
  assign tp_dbg[4] = pi_mosi_rdy;
  assign tp_dbg[5] = lb_wr_wide;
  assign tp_dbg[6] = lb_rd_wide;
  assign tp_dbg[7] = lb_rd_rdy_wide;
//assign tp_dbg[7:4] = tp_spi_dbg[3:0];
  assign dbg_pin = { 24'd0, tp_dbg[7:0] };


//-----------------------------------------------------------------------------
// Test Counter
//-----------------------------------------------------------------------------
always @ ( posedge clk_100m_tree ) begin : proc_wide
  lb_wr_p1       <= lb_wr;
  lb_rd_p1       <= lb_rd;
  lb_rd_rdy_p1   <= lb_rd_rdy;
  lb_wr_wide     <= lb_wr_p1 | lb_wr;
  lb_rd_wide     <= lb_rd_p1 | lb_rd;
  lb_rd_rdy_wide <= lb_rd_rdy_p1 | lb_rd_rdy;
end // proc_wide


//-----------------------------------------------------------------------------
// Test Counter. Only flashes LEDs now. Was used for GPIO HW tests.
//-----------------------------------------------------------------------------
always @ ( posedge clk_100m_tree ) begin : proc_div
 begin
   test_cnt <= test_cnt[31:0] + 1;
 end
end // proc_div


//-----------------------------------------------------------------------------
// IOB : PMODs are Bidirectional configurable, so instantiate Lattice Bidis
//-----------------------------------------------------------------------------
//genvar i0;
//generate
//for ( i0=0; i0<=7; i0=i0+1 ) begin: gen_i0
//buf_io u0_buf_io
//(
//  .CLK ( 1'b0             ),
//  .IO  ( pmod_p1_d[i0]    ),
//  .T   ( 1'b0             ),
//  .I   ( test_cnt[i0+24]  ),
//  .O   (                  )
// );
//buf_io u1_buf_io
//(
//  .CLK ( 1'b0             ),
//  .IO  ( pmod_p2_d[i0]    ),
//  .T   ( 1'b0             ),
//  .I   ( test_cnt[i0+0 ]  ),
//  .O   (                  )
// );
//buf_io u2_buf_io
//(
//  .CLK ( 1'b0             ),
//  .IO  ( pmod_p3_d[i0]    ),
//  .T   ( 1'b0             ),
//  .I   ( test_cnt[i0+24]  ),
//  .O   (                  )
// );
//buf_io u3_buf_io
//(
//  .CLK ( 1'b0             ),
//  .IO  ( pmod_p4_d[i0]    ),
//  .T   ( 1'b0             ),
//  .I   ( test_cnt[i0+24]  ),
//  .O   (                  )
// );
//end
//endgenerate


//-----------------------------------------------------------------------------
// PLL generated by Lattice GUI to multiply 25 MHz to 100 MHz
// PLL's RESET port is active low. How messed up of a signal name is that?
//-----------------------------------------------------------------------------
//top_pll u_top_pll
//(
//  .REFERENCECLK ( clk_25m       ),
//  .PLLOUTCORE   (               ),
//  .PLLOUTGLOBAL ( clk_100m_tree ),
//  .LOCK         ( pll_100m_lock ),
//  .RESET        ( 1'b1          )
//);


//-----------------------------------------------------------------------------
// Global Clock Tree Buffer
//-----------------------------------------------------------------------------
SB_GB u0_sb_gb
(
  .USER_SIGNAL_TO_GLOBAL_BUFFER ( clk_100m      ),
  .GLOBAL_BUFFER_OUTPUT         ( clk_100m_tree )
);


//-----------------------------------------------------------------------------
// core of GPIO+SUMP2
//-----------------------------------------------------------------------------
core u_core 
(
  .reset               ( 1'b0                     ),
  .clk_lb              ( clk_100m_tree            ),
  .clk_cap             ( clk_100m_tree            ),
  .lb_wr               ( lb_wr                    ),
  .lb_rd               ( lb_rd                    ),
  .lb_addr             ( lb_addr[31:0]            ),
  .lb_wr_d             ( lb_wr_d[31:0]            ),
  .lb_rd_d             ( lb_rd_d[31:0]            ),
  .lb_rd_rdy           ( lb_rd_rdy                ),
  .dbg_pin             ( dbg_pin[31:0]            ),
  .gpio_pin            ( gpio_pin[31:0]           ),
  .led_bus             ( led_bus[3:0]             )
);// module core


//-----------------------------------------------------------------------------
// Decode Mesa ID Request
//-----------------------------------------------------------------------------
always @ ( posedge clk_100m_tree ) begin : proc_decode_mesa_id
  mesa_id_req <= 0;
  if ( subslot_ctrl[8] == 1 && subslot_ctrl[7:4] == 4'hF ) begin
    if ( subslot_ctrl[3:0] == 4'hA ) begin
      mesa_id_req <= 1;
    end
  end
end // proc_decode_mesa_id


//-----------------------------------------------------------------------------
// MesaBus PI_SPI : SPI Interface for MesaBus from RaspPI SPI.
// This replaces traditional UART MesaBus interface for this design. 
// SPI should be both faster and smaller.
// This converts SPI to local fabric:
//   MOSI Wi : SPI to Nibbles for mesa_core 
//   MISO Ro : 32bit LocalBus Readback and also Mesa ID Requests
//-----------------------------------------------------------------------------
mesa_pi_spi u_mesa_pi_spi
(
  .clk                 ( clk_100m_tree       ),
  .pi_spi_sck          ( pi_spi_sck          ),
  .pi_spi_cs_l         ( pi_spi_cs_l         ),
  .pi_spi_mosi         ( pi_spi_mosi         ),
  .pi_spi_miso         ( pi_spi_miso         ),
  .mesa_id_req         ( mesa_id_req         ),
  .id_mfr              ( 32'h00000001        ),
  .id_dev              ( 32'h00000002        ),
  .id_snum             ( 32'hFFFFFFFF        ),
  .id_timestamp        ( time_stamp_d[31:0]  ),
  .lb_rd               ( lb_rd               ),
  .lb_rd_d             ( lb_rd_d[31:0]       ),
  .lb_rd_rdy           ( lb_rd_rdy           ),
  .tp_dbg              ( tp_spi_dbg[3:0]     ),
  .mosi_nib_d          ( pi_mosi_d[3:0]      ),
  .mosi_nib_rdy        ( pi_mosi_rdy         )
);// u_mesa_pi_spi


//-----------------------------------------------------------------------------
// 32bit UNIX TimeStamp of when the design was synthesized
//-----------------------------------------------------------------------------
time_stamp u_time_stamp
(
  .time_dout                        ( time_stamp_d                   )
);


//-----------------------------------------------------------------------------
// MesaBus decoder. Converts binary nibbles into 32bit LocalBus Wi,MOSI path
// Note: A bunch of legacy signals from UART MesaBus exist still.
//-----------------------------------------------------------------------------
mesa_core
#
(
  .spi_prom_en         ( 1'b0                     )
)
u_mesa_core
(
  .reset               ( 1'b0                     ),
  .clk                 ( clk_100m_tree            ),
  .spi_sck             (                          ),
  .spi_cs_l            (                          ),
  .spi_mosi            (                          ),
  .spi_miso            ( 1'b0                     ),
  .pi_mosi_d           ( pi_mosi_d[3:0]           ),
  .pi_mosi_rdy         ( pi_mosi_rdy              ),
  .rx_in_d             ( mesa_wi_nib_d[3:0]       ),
  .rx_in_rdy           ( mesa_wi_nib_en           ),
  .tx_byte_d           (                          ),
  .tx_byte_rdy         (                          ),
  .tx_done             (                          ),
  .tx_busy             ( 1'b0                     ),
  .tx_wo_byte          (                          ),
  .tx_wo_rdy           (                          ),
  .subslot_ctrl        ( subslot_ctrl[8:0]        ),
  .bist_req            (                          ),
  .reconfig_req        (                          ),
  .reconfig_addr       (                          ),
  .oob_en              ( 1'b0                     ),
  .oob_done            ( 1'b0                     ),
  .lb_wr               ( lb_wr                    ),
  .lb_rd               ( lb_rd                    ),
  .lb_wr_d             ( lb_wr_d[31:0]            ),
  .lb_addr             ( lb_addr[31:0]            ),
  .lb_rd_d             ( 32'd0                    ),
  .lb_rd_rdy           ( 1'b0                     )
);// module mesa_core
  assign mesa_wi_nib_d[3:0] = 4'd0;
  assign mesa_wi_nib_en     = 0;


endmodule // top.v
