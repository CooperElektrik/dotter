# Dotter

A small visual novel engine. 

Stories are written as `.p` screenplay files parsed by the 
[inProse](https://github.com/CooperElektrik/inProse) narrative DSL.

## Install

    git clone https://github.com/CooperElektrik/dotter
    cd dotter
    pip install -e .
    # Or
    pip install -e ".[dev]"

## Run

    dotter demo                     # built-in demo scene
    dotter run path/to/scene.p      # play a screenplay file
    dotter run scene.p --headless   # skip window/audio (testing)

`dotter demo --headless` runs the demo in verification mode without a window.