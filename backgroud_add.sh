#!/bin/bash
# -*- coding: UTF8 -*-

nohup ./r2k run && ./r2k add $1 && ./r2k run --no-send &
