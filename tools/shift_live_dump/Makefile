CXX ?= g++
CXXFLAGS ?= -O2 -g -std=c++17 -Wall -Wextra -Wpedantic

all: shift-live-dump

shift-live-dump: shift_live_dump.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

test: shift-live-dump
	bash test_smoke.sh
	bash test_analyze.sh
	bash test_analyze_fields.sh
	bash test_analyze_events.sh
	bash test_analyze_track_paths.sh
	bash test_verify_track_path_source_anchors.sh
	bash test_validate_aiw_runtime_graph.sh
	bash test_join_path_start_nodes.sh
	bash test_validate_track_path_instance_graph.sh
	bash test_audit_track_path_capture.sh

clean:
	rm -f shift-live-dump

.PHONY: all test clean
