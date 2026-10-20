// Define the verified retail method at 0x005a8870 from its exact instruction bytes.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.symbol.SourceType;

public class DefineShiftFunctionBody005A8870 extends GhidraScript {
    private static final long ENTRY = 0x005a8870L;
    private static final long END = 0x005a8959L;
    private static final int EXPECTED_INSTRUCTIONS = 64;
    private static final String VERIFIED_BYTES =
        "53bb01000000841dc0dbbb00568bf1751d091dc0dbbb00b900d1bb00e85f55fd" +
        "ff68b0aea900e81887350083c404b900d1bb00e848b53400841d40e0bb00751d" +
        "091d40e0bb00b9e0dbbb00e82079fdff68d0aea900e8e986350083c404b9e0db" +
        "bb00e8c97bfdff8b86482200008b50048d8e48220000ffd2841dc0dbbb00751d" +
        "091dc0dbbb00b900d1bb00e8f054fdff68b0aea900e8a986350083c404b900d1" +
        "bb00e8895cfdff8b46e08b90f400000083c6e06a008bceffd28b068b90fc0000" +
        "006a008bceffd28b068b90940200006a006a008bceffd28b068b908c0100006a" +
        "008bceffd25e33c05bc3";

    @Override
    public void run() throws Exception {
        Address entry = toAddr(ENTRY);
        Address end = toAddr(END);
        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        Function existing = functions.getFunctionAt(entry);
        if (existing == null && functions.getFunctionContaining(entry) != null) {
            throw new IllegalStateException(entry + " is inside another function");
        }

        byte[] bytes = new byte[VERIFIED_BYTES.length() / 2];
        memory.getBytes(entry, bytes);
        if (bytes.length != END - ENTRY + 1 ||
                !VERIFIED_BYTES.equals(hex(bytes))) {
            throw new IllegalStateException("retail bytes changed at " + entry);
        }

        int transaction = currentProgram.startTransaction(
            "Define verified FUN_005a8870");
        boolean commit = false;
        try {
            if (existing == null) clearListing(entry, end);
            Address cursor = entry;
            int instructionCount = 0;
            Instruction last = null;
            while (cursor.compareTo(end) <= 0) {
                Instruction instruction = listing.getInstructionAt(cursor);
                if (instruction == null) {
                    if (!disassemble(cursor)) {
                        throw new IllegalStateException("cannot disassemble " + cursor);
                    }
                    instruction = listing.getInstructionAt(cursor);
                }
                if (instruction == null || instruction.getMaxAddress().compareTo(end) > 0) {
                    throw new IllegalStateException("instruction coverage gap at " + cursor);
                }
                last = instruction;
                instructionCount++;
                cursor = instruction.getMaxAddress().next();
            }
            if (last == null || !last.getMaxAddress().equals(end) ||
                    !"RET".equals(last.getMnemonicString()) ||
                    instructionCount != EXPECTED_INSTRUCTIONS) {
                throw new IllegalStateException("function terminal or instruction count changed");
            }

            Function function = existing;
            if (function == null) {
                function = functions.createFunction(
                    "FUN_005a8870", entry, new AddressSet(entry, end),
                    SourceType.USER_DEFINED);
            }
            if (function == null) throw new IllegalStateException("function creation failed");
            function.setCallingConvention("__thiscall");
            if (function.getBody().getNumAddresses() != bytes.length ||
                    !entry.equals(function.getEntryPoint()) ||
                    !end.equals(function.getBody().getMaxAddress()) ||
                    !"__thiscall".equals(function.getCallingConventionName())) {
                throw new IllegalStateException("created function body is not exact");
            }
            commit = true;
            println("Defined verified FUN_005a8870; bytes=" + bytes.length +
                    " instructions=" + instructionCount + " calling_convention=__thiscall");
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) value.append(String.format("%02x", item & 0xff));
        return value.toString();
    }
}
