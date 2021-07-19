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
    input [1:0] I0,
    input [1:0] _Foo_Register_inst0_reg_P2_inst0_in,
    input [1:0] _Foo_Register_inst1_reg_P2_inst0_in,
    output [3:0] O,
    input lifted_input0,
    input lifted_input1,
    input lifted_input2,
    input lifted_input3,
    input CLK
);
wire [1:0] _Foo_Register_inst0_reg_P2_inst0_out;
wire [1:0] _Foo_Register_inst1_reg_P2_inst0_out;
wire [1:0] _Foo_magma_Bits_2_or_inst0_out;
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) _Foo_Register_inst0_reg_P2_inst0 (
    .clk(CLK),
    .in(_Foo_Register_inst0_reg_P2_inst0_in),
    .out(_Foo_Register_inst0_reg_P2_inst0_out)
);
coreir_reg #(
    .clk_posedge(1'b1),
    .init(2'h0),
    .width(2)
) _Foo_Register_inst1_reg_P2_inst0 (
    .clk(CLK),
    .in(_Foo_Register_inst1_reg_P2_inst0_in),
    .out(_Foo_Register_inst1_reg_P2_inst0_out)
);
assign _Foo_magma_Bits_2_or_inst0_out = ({lifted_input2,_Foo_Register_inst0_reg_P2_inst0_out[0]}) | ({lifted_input3,_Foo_Register_inst1_reg_P2_inst0_out[0]});
assign O = {lifted_input1,lifted_input0,~ I0[0],_Foo_magma_Bits_2_or_inst0_out[0]};
endmodule

