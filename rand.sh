#!/usr/bin/env bash
DIR=$(dirname "$(readlink -f "$0")")
shuf -n 1 "${DIR}/data/kanji_list" | tee "${DIR}/data/kanji_${TMUX_PANE}"
