.PHONY: test test-python test-rtl

test: test-python

test-python:
	PYTHONPATH=src python tests/run_tests.py

test-rtl:
	iverilog -g2012 -o /tmp/weaver_veto_sim hardware/veto_latch.sv hardware/tb_veto_latch.sv
	vvp /tmp/weaver_veto_sim
