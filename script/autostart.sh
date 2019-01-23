#!/bin/bash

# prepare args for app.py
datapath="../data"
logpath="./log"

function echo_help() {
    echo "arguments:
    --help
    --rm_pickles (removes .pickle files from ./data/tmp_pickles)
    --prepare_for_shipment (build frontend, zip some data)
    --reload_sskj_senses (removes author: SSKJ from db.v2_senses
        and inserts senses from ./data/no_del_pickles/sskj_sense.pickle)
    --debug"
}

function rm_pickles () {
    pickles_path="${datapath}/tmp_pickles"
    nfiles=$(ls "${pickles_path}" | grep ".pickle" | wc -l)
    if [[ $nfiles -gt 0 ]]; then
        echo "Removing:"
        ls "${pickles_path}"/*.pickle
        rm "${pickles_path}"/*.pickle
    else
        echo "No .pickle files to remove."
    fi
}

function prepare_for_shipment () {
    ./sherpa.sh --pack
    ./sherpa.sh --build_vue
}

args=""
# Parse arguments
while [[ "$#" -gt 0 ]]; do
    key="$1"
    case "$key" in
        --help)
            echo_help
            exit 0
            ;;
        --rm_pickles)
            rm_pickles
            exit 0
            ;;
        --prepare_for_shipment)
            prepare_for_shipment
            exit 0
            ;;
        --reload_sskj_senses)
            args="$args --reload_sskj_senses"
            shift
            ;;
        --debug)
            args="$args --debug"
            shift
            ;;
        *)
            echo "Unknown argument: $key"
            exit 1
            ;;
    esac
done


args="${args} --datapath=${datapath} --logpath=${logpath}"
python3 ./flask_app/app.py "$args"
