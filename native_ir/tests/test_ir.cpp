#include "shift_ir.hpp"
#include <cassert>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    auto mesh = shift::ir::loadMgeo(argv[1]);
    auto collision = shift::ir::loadCmesh(argv[2]);
    assert(mesh.positions.size() == 4);
    assert(mesh.indices.size() == 6);
    assert(mesh.uvLayers.size() == 1);
    assert(collision.positions.size() == 363);
    assert(collision.indices.size() == 1887);
    std::cout << "MGEO vertices=" << mesh.positions.size() << " indices=" << mesh.indices.size() << "\n";
    std::cout << "CMES vertices=" << collision.positions.size() << " indices=" << collision.indices.size() << "\n";
    return 0;
}
