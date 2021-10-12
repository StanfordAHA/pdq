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

module register_to_regsiter_partial (
    input I0,
    output O0,
    input CLK
);
wire Registered_magma_Bit_not_inst0_out;
wire [0:0] Registered_reg0_reg_P1_inst0_out;
wire [0:0] Registered_reg1_reg_P1_inst0_out;
assign Registered_magma_Bit_not_inst0_out = ~ Registered_reg0_reg_P1_inst0_out[0];
coreir_reg #(
    .clk_posedge(1'b1),
    .init(1'h0),
    .width(1)
) Registered_reg0_reg_P1_inst0 (
    .clk(CLK),
    .in(I0),
    .out(Registered_reg0_reg_P1_inst0_out)
);
coreir_reg #(
    .clk_posedge(1'b1),
    .init(1'h0),
    .width(1)
) Registered_reg1_reg_P1_inst0 (
    .clk(CLK),
    .in(Registered_magma_Bit_not_inst0_out),
    .out(Registered_reg1_reg_P1_inst0_out)
);
assign O0 = Registered_reg1_reg_P1_inst0_out[0];
endmodule

