module _Foo_Partial (
    output O,
    input ifc_x,
    output ifc_y
);
wire _Foo_magma_Bit_not_inst0_out;
assign _Foo_magma_Bit_not_inst0_out = ~ ifc_x;
assign O = _Foo_magma_Bit_not_inst0_out;
assign ifc_y = _Foo_magma_Bit_not_inst0_out;
endmodule

