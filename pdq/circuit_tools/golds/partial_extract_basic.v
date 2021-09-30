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

module _Foo_Partial (
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
wire [1:0] _Foo_Register_inst0_reg_P2_inst0_out;
wire [1:0] _Foo_Register_inst1_reg_P2_inst0_out;
wire [1:0] _Foo_magma_Bits_2_or_inst0_out;
wire [1:0] _Foo_Register_inst0_reg_P2_inst0_in;
assign _Foo_Register_inst0_reg_P2_inst0_in = {I4,I3};
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) _Foo_Register_inst0_reg_P2_inst0 (
    .clk(CLK),
    .in(_Foo_Register_inst0_reg_P2_inst0_in),
    .out(_Foo_Register_inst0_reg_P2_inst0_out)
);
wire [1:0] _Foo_Register_inst1_reg_P2_inst0_in;
assign _Foo_Register_inst1_reg_P2_inst0_in = {I6,I5};
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) _Foo_Register_inst1_reg_P2_inst0 (
    .clk(CLK),
    .in(_Foo_Register_inst1_reg_P2_inst0_in),
    .out(_Foo_Register_inst1_reg_P2_inst0_out)
);
assign _Foo_magma_Bits_2_or_inst0_out = ({I1,_Foo_Register_inst0_reg_P2_inst0_out[0]}) | ({I2,_Foo_Register_inst1_reg_P2_inst0_out[0]});
assign O0 = _Foo_magma_Bits_2_or_inst0_out[0];
assign O1 = ~ I0;
assign O2 = _Foo_magma_Bits_2_or_inst0_out[1];
assign O3 = _Foo_Register_inst0_reg_P2_inst0_out[1];
assign O4 = _Foo_Register_inst1_reg_P2_inst0_out[1];
endmodule

