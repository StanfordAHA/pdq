module coreir_reg #(
    parameter width = 1,
    parameter clk_posedge = 1,
    parameter init = 1
) (
    input clk,
    input [width-1:0] in,
    output [width-1:0] out
);
  reg [width-1:0] outReg=init;
  wire real_clk;
  assign real_clk = clk_posedge ? clk : ~clk;
  always @(posedge real_clk) begin
    outReg <= in;
  end
  assign out = outReg;
endmodule

module basic_partial (
    input I0,
    input I1,
    input I2,
    input I3,
    input I4,
    input I5,
    input I6,
    output O0,
    output O1,
    output O2,
    output O3,
    output O4,
    input CLK
);
wire [1:0] Basic_Register_inst0_reg_P2_inst0_out;
wire [1:0] Basic_Register_inst1_reg_P2_inst0_out;
wire [1:0] Basic_magma_Bits_2_or_inst0_out;
wire [1:0] Basic_Register_inst0_reg_P2_inst0_in;
assign Basic_Register_inst0_reg_P2_inst0_in = {I4,I3};
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) Basic_Register_inst0_reg_P2_inst0 (
    .clk(CLK),
    .in(Basic_Register_inst0_reg_P2_inst0_in),
    .out(Basic_Register_inst0_reg_P2_inst0_out)
);
wire [1:0] Basic_Register_inst1_reg_P2_inst0_in;
assign Basic_Register_inst1_reg_P2_inst0_in = {I6,I5};
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) Basic_Register_inst1_reg_P2_inst0 (
    .clk(CLK),
    .in(Basic_Register_inst1_reg_P2_inst0_in),
    .out(Basic_Register_inst1_reg_P2_inst0_out)
);
assign Basic_magma_Bits_2_or_inst0_out = ({I1,Basic_Register_inst0_reg_P2_inst0_out[0]}) | ({I2,Basic_Register_inst1_reg_P2_inst0_out[0]});
assign O0 = Basic_magma_Bits_2_or_inst0_out[0];
assign O1 = ~ I0;
assign O2 = Basic_magma_Bits_2_or_inst0_out[1];
assign O3 = Basic_Register_inst0_reg_P2_inst0_out[1];
assign O4 = Basic_Register_inst1_reg_P2_inst0_out[1];
endmodule

