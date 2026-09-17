#!/bin/bash

git clone https://github.com/johndeckardsoftware/digitalframe.git
cd digitalframe
python -m venv venv/
source venv/bin/activate
pip install -r requirements.txt
echo "python ./src/df.py"
echo "python ./src/df.py --fullscreen"
