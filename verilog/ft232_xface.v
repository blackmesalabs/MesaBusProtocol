/* ****************************************************************************
-- Source file: ft232_xface.v                
-- Date:        June 8, 2016    
-- Author:      khubbard
-- Description: Top Level Verilog RTL for Mesa Bus Backdoor interface to UART
-- Language:    Verilog-2001 and VHDL-1993
-- Simulation:  Mentor-Modelsim 
-- Synthesis:   Xilinxt XST or Lattice     
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   06.08.16  khubbard Creation
-- ***************************************************************************/
`default_nettype none // Strictly enforce all nets to be declared

module ft232_xface 
(
  input  wire         reset,
  input  wire         clk_lb,
  input  wire         ftdi_wi,
  output wire         ftdi_ro,

  output wire         lb_wr,
  output wire         lb_rd,
  output wire [31:0]  lb_addr,
  output wire [31:0]  lb_wr_d,
  input  wire [31:0]  lb_rd_d,
  input  wire         lb_rd_rdy

//inout  wire         ftdi_wo,
//inout  wire         ftdi_ri,

//output wire         prom_wr,
//output wire         prom_rd,
//output wire [31:0]  prom_addr,
//output wire [31:0]  prom_wr_d,
//input  wire [31:0]  prom_rd_d,
//input  wire         prom_rd_rdy 
);// module ft232_xface

  reg           cks_off_req;

  reg           reset_core;
  wire          reset_loc;

  reg           bd_ro_muxd;
  wire          mesa_wo_loc;
  wire          mesa_ri_loc;
  reg           mesa_wo_muxd;

  wire          mesa_wi_flush;
  wire          mesa_wi_loc;
  wire          mesa_wi_nib_en;
  wire [3:0]    mesa_wi_nib_d;
  wire          mesa_wo_byte_en;
  wire [7:0]    mesa_wo_byte_d;
  wire          mesa_wo_busy;
  wire          mesa_ro_byte_en;
  wire [7:0]    mesa_ro_byte_d;
  wire          mesa_ro_busy;
  wire          mesa_ro_done;
  wire          mesa_ro_loc;

  wire [7:0]    rx_loc_d;
  wire          rx_loc_rdy;
  wire          rx_loc_start;
  wire          rx_loc_stop;

  wire [7:0]    core_ro_byte_d;
  wire          core_ro_byte_en;
  wire          core_ro_done;
  wire          core_ro_busy;
  wire [8:0]    subslot_ctrl;
  reg  [3:0]    tx_busy_sr;

  reg           prom_boot_en;
  reg  [1:0]    prom_boot_sel;
  reg  [1:0]    pin_ctrl_ro;
  reg  [1:0]    pin_ctrl_wo;
  reg           pin_ctrl_ri;
  reg           clr_baudlock;
  wire          int_l_loc;
  wire          user_wo;
  wire          user_ro;
  reg           reboot_req;
  reg           report_id;

  wire          ftdi_ri_oe_l;
  wire          ftdi_ri_in;
  wire          ftdi_ri_out;
  wire          ftdi_wo_out;
  reg           ftdi_wo_oe_l;


  assign reset_loc    = reset;
  assign int_l_loc    = 1;
  assign user_ro      = 1;// User function for ro

//iob_bidi u2_out ( .IO( ftdi_wo       ), .T( ftdi_wo_oe_l   ),
//                  .I ( ftdi_wo_out   ), .O(                ));
//
//iob_bidi u1_out ( .IO( ftdi_ri       ), .T( 1'b1           ),
//                  .I ( ftdi_ri_out   ), .O( ftdi_ri_in     ));


  assign ftdi_ri_oe_l = ~ pin_ctrl_ri;// Ri becomes an output if User_Ri sel
  assign ftdi_ri_out = 1'b1;
  assign ftdi_ro     = ( ~ bd_ro_muxd );
  assign ftdi_wo_out = ~mesa_wo_muxd;
//assign mesa_ri_loc = ( pin_ctrl_ri == 0 ) ? ftdi_ri_in : 1;
  assign mesa_ri_loc = 1'b1;
  assign mesa_wi_loc = ftdi_wi;


//-----------------------------------------------------------------------------
// Subslot Control bits control muxes for pin functions
// 0x0 = Ro pin is MesaBus Ro Readback     ( Default )
// 0x1 = Ro pin is MesaBus Wi loopback
// 0x2 = Ro pin is MesaBus Interrupt
// 0x3 = Ro pin is user defined output function
// 0x4 = Wo pin is MesaBus Wo Write-Out    ( Default )
// 0x5 = Wo pin is MesaBus Wi loopback
// 0x6 = Wo pin is MesaBus Interrupt
// 0x7 = Wo pin is user defined function
// 0x8 = Ri pin is MesaBus Ri Read-In      ( Default )
// 0x9 = Ri pin is user defined input function. Ri is disabled.
//
// Ro pin is active Low and is used for both serial readback and interrupts
// Use combinatorial AND between internal Ro and incoming Ri
// Note: Inversions to try and keep logic '1' after reset instead of 0
//
// Wo pin may be used for Wo, Interrupt, Wi Loopback or User Function
//-----------------------------------------------------------------------------
always @ ( posedge clk_lb ) begin : proc_wo_mux
 case( pin_ctrl_ro[1:0] )
   default : bd_ro_muxd   <= ~mesa_ro_loc;
   2'd1    : bd_ro_muxd   <= ~mesa_wi_loc;// Wi Loopback to Ro
   2'd2    : bd_ro_muxd   <= ~int_l_loc;
   2'd3    : bd_ro_muxd   <= ~user_ro;
 endcase
 case( pin_ctrl_wo[1:0] )
   default : mesa_wo_muxd <= ~mesa_wo_loc;
   2'd1    : mesa_wo_muxd <= ~ftdi_wi;
   2'd2    : mesa_wo_muxd <= ~int_l_loc;
   2'd3    : mesa_wo_muxd <= ~user_wo;
 endcase
//mesa_wo_muxd <= ~user_wo;

end // proc_wo_mux 


//-----------------------------------------------------------------------------
// Wo is tristated until bus goes active.
//-----------------------------------------------------------------------------
always @ ( posedge clk_lb ) begin : proc_wo_oe
  if ( reset_loc == 1 ) begin
    ftdi_wo_oe_l <= 1;// Tristate Wo until bus goes active
  end else if ( ftdi_wi == 0 ) begin
    ftdi_wo_oe_l <= 0;
  end 
end // proc_wo_oe


//-----------------------------------------------------------------------------
// Subslot Control : Decode subslot control nibbles for pin functions,etc
//-----------------------------------------------------------------------------
always @ ( posedge clk_lb ) begin : proc_subslot_ctrl
  clr_baudlock     <= 0;
  report_id        <= 0;
  reset_core       <= 0;
  prom_boot_sel[1] <= 0;
  prom_boot_sel[0] <= 0;// 1st or 2nd slot
  prom_boot_en     <= 0;
  cks_off_req      <= 0;
  if ( subslot_ctrl[8] == 1 && subslot_ctrl[7:4] == 4'hF ) begin
    if ( subslot_ctrl[3:2] == 2'b00 ) begin
      pin_ctrl_ro <= subslot_ctrl[1:0];// 0-3
    end
    if ( subslot_ctrl[3:2] == 2'b01 ) begin
      pin_ctrl_wo <= subslot_ctrl[1:0];// 4-7
    end
    if ( subslot_ctrl[3:0] == 4'h8 ) begin
      pin_ctrl_ri   <= 0;
    end
    if ( subslot_ctrl[3:0] == 4'h9 ) begin
      pin_ctrl_ri   <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hA ) begin
      report_id     <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hB ) begin
      reset_core    <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hC ) begin
      clr_baudlock  <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hD ) begin
      cks_off_req   <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hE ) begin
      prom_boot_sel[0] <= 0;// 1st slot
      prom_boot_en     <= 1;
    end
    if ( subslot_ctrl[3:0] == 4'hF ) begin
      prom_boot_sel[0] <= 1;// 2nd slot
      prom_boot_en     <= 1;
    end
  end

  if ( reset_loc == 1 ) begin
    reset_core      <= 1;
    pin_ctrl_ro     <= 2'd0;
    pin_ctrl_wo     <= 2'd0;
    pin_ctrl_ri     <= 0;
  end
end // proc_subslot_ctrl


//-----------------------------------------------------------------------------
// MesaBus Phy : Convert UART serial to/from binary for Mesa Bus Interface
//-----------------------------------------------------------------------------
mesa_uart_phy u_mesa_uart_phy
(
  .reset                 ( reset_loc           ),
  .clk                   ( clk_lb              ),
  .clr_baudlock          ( clr_baudlock        ),
  .uart_baud             (                     ),
  .dbg_rx                (                     ),
  .dbg_out               (                     ),
  .user_wo               ( user_wo             ),
  .mesa_wi               ( mesa_wi_loc         ),
  .mesa_ro               ( mesa_ro_loc         ),
  .mesa_wo               ( mesa_wo_loc         ),
  .mesa_ri               ( mesa_ri_loc         ),
  .mesa_wi_flush         ( mesa_wi_flush       ),
  .mesa_wi_nib_en        ( mesa_wi_nib_en      ),
  .mesa_wi_nib_d         ( mesa_wi_nib_d[3:0]  ),

  .mesa_wo_byte_en       ( mesa_wo_byte_en     ),
  .mesa_wo_byte_d        ( mesa_wo_byte_d[7:0] ),

  .mesa_wo_busy          ( mesa_wo_busy        ),
  .mesa_ro_byte_en       ( mesa_ro_byte_en     ),
  .mesa_ro_byte_d        ( mesa_ro_byte_d[7:0] ),
  .mesa_ro_busy          ( mesa_ro_busy        ),
  .mesa_ro_done          ( mesa_ro_done        )
);// module mesa_uart_phy


//-----------------------------------------------------------------------------
// Decode Slot Addresses : Take in the Wi path as nibbles and generate the Wo
// paths for both internal and external devices.
//-----------------------------------------------------------------------------
mesa_decode u_mesa_decode
(
  .clk                   ( clk_lb              ),
  .reset                 ( reset               ),
  .rx_in_flush           ( mesa_wi_flush       ),
  .rx_in_rdy             ( mesa_wi_nib_en      ),
  .rx_in_d               ( mesa_wi_nib_d[3:0]  ),
  .rx_out_d              ( mesa_wo_byte_d[7:0] ),
  .rx_out_rdy            ( mesa_wo_byte_en     ),
  .rx_loc_d              ( rx_loc_d[7:0]       ),
  .rx_loc_rdy            ( rx_loc_rdy          ),
  .rx_loc_start          ( rx_loc_start        ),
  .rx_loc_stop           ( rx_loc_stop         )
);


//-----------------------------------------------------------------------------
// Convert Subslots 0x0 and 0xE to 32bit local bus for user logic and prom
//-----------------------------------------------------------------------------
mesa2lb u_mesa2lb
(
  .clk                   ( clk_lb              ),
  .reset                 ( reset               ),
  .mode_usb3             ( 1'b0                ),
  .rx_byte_d             ( rx_loc_d[7:0]       ),
  .rx_byte_rdy           ( rx_loc_rdy          ),
  .rx_byte_start         ( rx_loc_start        ),
  .rx_byte_stop          ( rx_loc_stop         ),

  .tx_byte_d             ( core_ro_byte_d[7:0] ),
  .tx_byte_rdy           ( core_ro_byte_en     ),
  .tx_done               ( core_ro_done        ),
  .tx_busy               ( core_ro_busy        ),

  .lb_wr                 ( lb_wr               ),
  .lb_rd                 ( lb_rd               ),
  .lb_wr_d               ( lb_wr_d[31:0]       ),
  .lb_addr               ( lb_addr[31:0]       ),
  .lb_rd_d               ( lb_rd_d[31:0]       ),
  .lb_rd_rdy             ( lb_rd_rdy           ),

  .prom_wr               (                     ),
  .prom_rd               (                     ),
  .prom_wr_d             (                     ),
  .prom_addr             (                     ),
  .prom_rd_d             ( 32'd0               ),
  .prom_rd_rdy           ( 1'b0                )

//.prom_wr               ( prom_wr             ),
//.prom_rd               ( prom_rd             ),
//.prom_wr_d             ( prom_wr_d[31:0]     ),
//.prom_addr             ( prom_addr[31:0]     ),
//.prom_rd_d             ( prom_rd_d[31:0]     ),
//.prom_rd_rdy           ( prom_rd_rdy         )
);


//-----------------------------------------------------------------------------
// FSM for reporting ID : This also muxes in Ro Byte path from Core
//-----------------------------------------------------------------------------
mesa_id u_mesa_id
(
  .reset                 ( reset_loc                ),
  .clk                   ( clk_lb                   ),
  .report_id             ( report_id                ),
  .id_mfr                ( 32'h00000001             ),
  .id_dev                ( 32'h00000001             ),
  .id_snum               ( 32'h00000001             ),
  .mesa_core_ro_byte_en  ( core_ro_byte_en          ),
  .mesa_core_ro_byte_d   ( core_ro_byte_d[7:0]      ),
  .mesa_core_ro_done     ( core_ro_done             ),
  .mesa_ro_byte_en       ( mesa_ro_byte_en          ),
  .mesa_ro_byte_d        ( mesa_ro_byte_d[7:0]      ),
  .mesa_ro_done          ( mesa_ro_done             ),
  .mesa_ro_busy          ( mesa_ro_busy             )
);// module mesa_id


// ----------------------------------------------------------------------------
// Support pipeling Ro byte path by asserting busy for 4 clocks after a byte
// ----------------------------------------------------------------------------
always @ ( posedge clk_lb ) begin : proc_tx
  tx_busy_sr[0]   <= core_ro_byte_en | mesa_ro_busy;
  tx_busy_sr[3:1] <= tx_busy_sr[2:0];
end // proc_tx
  assign core_ro_busy = ( tx_busy_sr != 4'b0000 ) ? 1 : 0;


//-----------------------------------------------------------------------------
// Decode Subslot Nibble Controls : Used for Pin Reassigns,ReportID,ResetCore
//-----------------------------------------------------------------------------
mesa2ctrl u_mesa2ctrl
(
  .clk                   ( clk_lb              ),
  .reset                 ( reset               ),
  .rx_byte_d             ( rx_loc_d[7:0]       ),
  .rx_byte_rdy           ( rx_loc_rdy          ),
  .rx_byte_start         ( rx_loc_start        ),
  .rx_byte_stop          ( rx_loc_stop         ),
  .subslot_ctrl          ( subslot_ctrl[8:0]   )
);


endmodule // ft232_xface.v
`default_nettype wire // enable Verilog default for any 3rd party IP needing it
