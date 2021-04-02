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

  adk_name = 'freepdk-45nm'
  adk_view = 'view-standard'
  design_name = '{{ design_name }}'

  parameters = {
    'construct_path' : __file__,
    'design_name'    : design_name,
    'testbench_name' : f"{design_name}_tb",
    'dut_name'       : design_name,
    'clock_period'   : {{ clock_period }},
    'adk'            : adk_name,
    'adk_view'       : adk_view,
    'topographical'  : True,
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
  ptpx_gl     = Step( this_dir + '/synopsys-ptpx-gl-post-synth' )

  # Default steps

  info           = Step( 'info',                           default=True )
  vcd2saif       = Step( 'synopsys-vcd2saif-convert',      default=True )
  sim            = Step( 'synopsys-vcs-sim',               default=True )

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

  g.connect( synth.o('design.v'), sim.i('design.vcs.v') )

  g.connect_by_name( testbench,      sim               )
  g.connect_by_name( vcd2saif,       sim               )

  g.connect_by_name( sim,            vcd2saif          )
  g.connect_by_name( vcd2saif,       ptpx_gl           )


  #-----------------------------------------------------------------------
  # Parameterize
  #-----------------------------------------------------------------------

  g.update_params( parameters )

  return g


if __name__ == '__main__':
  g = construct()
#  g.plot()
