CXX ?= g++
CXXFLAGS ?= -O2 -g -std=c++17 -Wall -Wextra -Wpedantic

all: shift-live-dump

shift-live-dump: shift_live_dump.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

clean:
	rm -f shift-live-dump

.PHONY: all clean
