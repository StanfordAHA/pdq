module corebit_undriven (
    output out
);

endmodule

module _Foo_Partial (
    input I0,
    input I1,
    input I2,
    output O0,
    output O1
);
wire [1:0] _Foo_magma_Bits_2_or_inst0_out;
wire corebit_undriven_inst0_out;
wire corebit_undriven_inst1_out;
assign _Foo_magma_Bits_2_or_inst0_out = ({corebit_undriven_inst0_out,I1}) | ({corebit_undriven_inst1_out,I2});
corebit_undriven corebit_undriven_inst0 (
    .out(corebit_undriven_inst0_out)
);
corebit_undriven corebit_undriven_inst1 (
    .out(corebit_undriven_inst1_out)
);
assign O0 = _Foo_magma_Bits_2_or_inst0_out[0];
assign O1 = ~ I0;
endmodule

