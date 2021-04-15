# PDQ

Queryable physical design

# Setup
We recommend using a python virtual environment. The required python packages are listed in `requirements.txt`.

    python -m venv env
    # Use activate.csh if on tcsh.
    source env/bin/activate
    python -m pip install -r requirements.txt
  
The `magma_examples` repo can be fetched locally for use in experimentation:

    git submodule update --init --recursive

# Running tests
Tests can be run using pytest:

    python -m pip install pytest
    python -m pytest pdq/

# Running
Assuming you have access to the necessary physical design tools, code can be run using:

    python basic_flow_main.py <design_package_name> [--module <module_name> | --generator <generator_name>] [--params <key>=<value>,...]

This will run the query flow on either the specified module or generator from `<design_package_name>`. `<design_package_name>` should be specified as a "dot" path rather than a file path. For example, to run on the `Adder` generator found in the file `magma_examples/magma_examples/adder.py`, we could run

    python main.py magma_examples.magma_examples.adder --generator Adder --params n=16
