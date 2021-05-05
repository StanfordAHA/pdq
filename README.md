# PDQ

Queryable physical design

# Setup
We recommend using a python virtual environment. For the base project, the required python packages are listed in `requirements.txt`.

    python -m venv env
    # Use activate.csh if on tcsh.
    source env/bin/activate
    python -m pip install -r requirements.txt

To get more designs for experimentation, there are some included submodules, such as `garnet`. Use the `git submodule` command to fetch these:

    git submodule update --init --recursive

Some submodules require their own requirements, contained in `<submodule>-requirements.txt`. E.g. for garnet related experiments:

    python -m pip install -r garnet-requirements.txt

# Running tests
Tests can be run using pytest:

    python -m pip install pytest
    python -m pytest pdq/

# Running
Assuming you have access to the necessary physical design tools, code can be run using:

    python basic_flow_main.py --package <design_package_name> [--module <module_name> | --generator <generator_name>] [--params <key>=<value>,...]

This will run the query flow on either the specified module or generator from `<design_package_name>`. `<design_package_name>` should be specified as a "dot" path rather than a file path. For example, to run on the `Adder` generator found in the file `magma_examples/magma_examples/adder.py`, we could run

    python main.py magma_examples.magma_examples.adder --generator Adder --params n=16
