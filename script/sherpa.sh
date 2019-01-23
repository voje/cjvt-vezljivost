#!/bin/bash

function echo_help () {
    echo "
sherpa.sh
    --help
    --pack (zip watched files)
    --unpack (unzip watched files)
    --list (list watched files)
    --build_vue (requires npm, builds vue_frontend for production)
    "
}

function frontend_config () {
    orig_path="$(pwd)"
    cd ./vue_frontend/config/
    if [[ $1 == "dev" ]]; then
        cp config_dev.json config.json
    elif [[ $1 == "pro" ]]; then
        cp config_pro.json config.json
    fi
    echo "Using config: "
    cat config.json
    cd "${orig_path}"
}

function build_vue () {
    echo "
API settings, pick a number:
----------------------------
1) development (API on localhost) 
2) production (see conf. files in vue folder for IP settings)
    "
    read choice
    if [ $choice == 1 ]; then
        frontend_config "dev"
    elif [ $choice == 2]; then
        frontend_config "pro"
    else
        exit
    fi
    orig_path="$(pwd)"
    cd ./vue_frontend
    npm run build
    cd "${orig_path}"
    if [ -d ./flask_app/vue/dist ]; then
        rm -r ./flask_app/vue/dist
    fi
    cp -r ./vue_frontend/dist/ ./flask_app/vue/
}

function unpack () {
    orig_path="$(pwd)"
    cd ../data/
    unzip ./no_del_pickles.zip
    cd "$orig_path"
}

function pack () {
    orig_path="$(pwd)"
    cd ../data/
    zip -r no_del_pickles.zip ./no_del_pickles/
    rm -r ./no_del_pickles
    cd "$orig_path"
}

if [[ "$#" -eq 0 ]]; then
    echo_help
fi

while [[ "$#" -gt 0 ]]; do
    key="$1"
    case "$key" in
        --help)
            echo_help
            exit 0
            ;;
        --pack)
            pack
            exit 0
            ;;
        --unpack)
            unpack
            exit 0
            ;;
        --build_vue)
            build_vue
            exit 0
            ;;
        --frontend_config)
            shift
            arg1="$1"
            frontend_config "$arg1"
            exit 0
            ;;
        *)
            echo_help
            exit 0
        shift
    esac
done
