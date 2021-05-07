#=========================================================================
# construct.py
#=========================================================================

import os

from mflowgen.components import Graph, Step

def construct():

  g = Graph()

  #-----------------------------------------------------------------------
  # Parameters
  #-----------------------------------------------------------------------

  adk_name = '{{adk_name}}'
  adk_view = 'view-standard'
  design_name = '{{ design_name }}'
  tb_name = f"{design_name}_tb"
  clock_net = {{ clock_net }}
  is_comb = clock_net is None

  parameters = {
    'construct_path' : __file__,
    'design_name'    : design_name,
    'clock_net'      : clock_net,
    'is_comb'        : is_comb,
    'testbench_name' : tb_name,
    'dut_name'       : design_name,
    'clock_period'   : {{ clock_period }},
    'adk'            : adk_name,
    'adk_view'       : adk_view,
    'topographical'  : True,
    'explore'        : {{ explore }},
    'strip_path'     : f"{tb_name}/dut"
  }

  #-----------------------------------------------------------------------
  # Create nodes
  #-----------------------------------------------------------------------

  this_dir = os.path.dirname( os.path.abspath( __file__ ) )

  # ADK step

  g.set_adk( adk_name )
  adk = g.get_adk_step()

  # Custom steps

  rtl         = Step( this_dir + '/rtl' )
  constraints = Step( this_dir + '/constraints' )
  synth       = Step( this_dir + '/synopsys-dc-synthesis' )
  synth_query = Step( this_dir + '/synopsys-dc-query' )
  testbench   = Step( this_dir + '/testbench' )

  # Default steps

  info        = Step( 'info',                           default=True )
  vcd2saif    = Step( 'synopsys-vcd2saif-convert',      default=True )
  sim         = Step( 'synopsys-vcs-sim',               default=True )
  ptpx_gl     = Step( 'synopsys-ptpx-gl',    default=True )

  #-----------------------------------------------------------------------
  # Graph -- Add nodes
  #-----------------------------------------------------------------------

  g.add_step( info           )
  g.add_step( rtl            )
  g.add_step( constraints    )
  g.add_step( synth          )
  g.add_step( synth_query    )
  g.add_step( testbench      )
  g.add_step( sim            )
  g.add_step( vcd2saif       )
  g.add_step( ptpx_gl        )

  #-----------------------------------------------------------------------
  # Graph -- Add edges
  #-----------------------------------------------------------------------

  # Connect by name

  g.connect_by_name( adk,            synth             )
  g.connect_by_name( adk,            synth_query       )
  g.connect_by_name( adk,            ptpx_gl           )
  g.connect_by_name( adk,            sim               )

  g.connect_by_name( rtl,            synth             )
  g.connect_by_name( constraints,    synth             )

  g.connect_by_name( synth,          synth_query       )
  g.connect_by_name( synth,          ptpx_gl           )


  g.connect( synth.o('design.v'), ptpx_gl.i('design.vcs.v') )
  g.connect( synth.o('design.sdc'), ptpx_gl.i('design.pt.sdc') )

  g.connect( synth.o('design.v'), sim.i('design.vcs.v') )

  g.connect_by_name( testbench,      sim               )
  g.connect_by_name( vcd2saif,       sim               )

  g.connect_by_name( sim,            vcd2saif          )
  g.connect_by_name( vcd2saif,       ptpx_gl           )


  #-----------------------------------------------------------------------
  # Parameterize
  #-----------------------------------------------------------------------

  g.update_params( parameters )

  synth.update_params( {
    'clock_net': parameters['clock_net'],
    'is_comb'  : parameters['is_comb']
    }, allow_new=True )

  return g


if __name__ == '__main__':
  g = construct()
#  g.plot()
