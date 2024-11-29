/* ****************************************************************************
-- Source file: iob_bidi.v                
-- Date:        February 2016    
-- Author:      khubbard
-- Description: Infer a simple single ended bidirectional IO buffer.
-- Language:    Verilog-2001 
-- Simulation:  Mentor-Modelsim 
-- Synthesis:   Lattice     
--
-- Revision History:
-- Ver#  When      Who      What
-- ----  --------  -------- ---------------------------------------------------
-- 0.1   02.01.16  khubbard Creation
-- ***************************************************************************/
`default_nettype none // Strictly enforce all nets to be declared

module iob_bidi
(
  input  wire         I,
  input  wire         T,
  output wire         O,
  inout  wire         IO
);// module iob_bidi

  assign IO = ( T == 1 ) ? 1'bz : I;
  assign O  = IO;

endmodule // iob_bidi.v
