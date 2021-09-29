module _Foo_Partial (
    input I0,
    input I1,
    input I2,
    input I3,
    input I4,
    output O0,
    output O1
);
wire [1:0] _Foo_magma_Bits_2_or_inst0_out;
assign _Foo_magma_Bits_2_or_inst0_out = ({I3,I1}) | ({I4,I2});
assign O0 = _Foo_magma_Bits_2_or_inst0_out[0];
assign O1 = ~ I0;
endmodule

