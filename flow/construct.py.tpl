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

  width = {{ width }}

  parameters = {
    'construct_path' : __file__,
    'design_name'    : f"RegisteredIncrementer{width}",
    'clock_period'   : {{ clock_period }},
    'adk'            : adk_name,
    'adk_view'       : adk_view,
    'topographical'  : True,
    'width'          : width
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
  synth       = Step( this_dir + '/synopsys-dc-synthesis')
  synth_query = Step( this_dir + '/synopsys-dc-query')

  # Default steps

  info           = Step( 'info',                           default=True )

  #-----------------------------------------------------------------------
  # Graph -- Add nodes
  #-----------------------------------------------------------------------

  g.add_step( info           )
  g.add_step( rtl            )
  g.add_step( constraints    )
  g.add_step( synth          )
  g.add_step( synth_query    )

  #-----------------------------------------------------------------------
  # Graph -- Add edges
  #-----------------------------------------------------------------------

  # Connect by name

  g.connect_by_name( adk,            synth             )
  g.connect_by_name( adk,            synth_query       )

  g.connect_by_name( rtl,            synth             )
  g.connect_by_name( constraints,    synth             )
  
  g.connect_by_name( synth,          synth_query       )

  #-----------------------------------------------------------------------
  # Parameterize
  #-----------------------------------------------------------------------

  g.update_params( parameters )

  return g


if __name__ == '__main__':
  g = construct()
#  g.plot()
