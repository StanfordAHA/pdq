module _Foo_Partial (
    input [1:0] I0,
    input [1:0] I1,
    output O2,
    output O0,
    output O3,
    output O1,
    input lifted_input0,
    input lifted_input1
);
wire [1:0] _Foo_magma_Bits_2_or_inst0_out;
assign _Foo_magma_Bits_2_or_inst0_out = ({lifted_input0,I0[0]}) | ({lifted_input1,I1[0]});
assign O2 = ~ _Foo_magma_Bits_2_or_inst0_out[0];
assign O0 = _Foo_magma_Bits_2_or_inst0_out[0];
assign O3 = _Foo_magma_Bits_2_or_inst0_out[1];
assign O1 = ~ (~ _Foo_magma_Bits_2_or_inst0_out[0]);
endmodule

