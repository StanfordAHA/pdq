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

module coreir_add #(
    parameter width = 1
) (
    input [width-1:0] in0,
    input [width-1:0] in1,
    output [width-1:0] out
);
  assign out = in0 + in1;
endmodule

module Register (
    input [31:0] I,
    output [31:0] O,
    input CLK
);
wire [31:0] reg_P_inst0_out;
coreir_reg #(
    .clk_posedge(1'b1),
    .init(32'h00000000),
    .width(32)
) reg_P_inst0 (
    .clk(CLK),
    .in(I),
    .out(reg_P_inst0_out)
);
assign O = reg_P_inst0_out;
endmodule

module RegisteredIncrementer32 (
    input [31:0] I0,
    input [31:0] I1,
    output [31:0] O,
    input CLK
);
wire [31:0] Register_inst0_O;
wire [31:0] magma_Bits_32_add_inst0_out;
Register Register_inst0 (
    .I(I0),
    .O(Register_inst0_O),
    .CLK(CLK)
);
coreir_add #(
    .width(32)
) magma_Bits_32_add_inst0 (
    .in0(Register_inst0_O),
    .in1(I1),
    .out(magma_Bits_32_add_inst0_out)
);
assign O = magma_Bits_32_add_inst0_out;
endmodule

