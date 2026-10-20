// Define the verified indirect-call target at 0x005b6e00.
//@category SHIFT.Recovery

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.Memory;

public class DefineShiftFunctionBody005B6E00 extends GhidraScript {
    private static final long ENTRY = 0x005b6e00L;
    private static final String VERIFIED_BYTES = "8d4110c20800cccccccccccccccccccc";

    @Override
    public void run() throws Exception {
        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        Address entry = toAddr(ENTRY);

        Function existing = functions.getFunctionAt(entry);
        if (existing != null || functions.getFunctionContaining(entry) != null) {
            throw new IllegalStateException("0x005b6e00 already belongs to a Ghidra function");
        }

        byte[] bytes = new byte[16];
        memory.getBytes(entry, bytes);
        if (!VERIFIED_BYTES.equals(hex(bytes))) {
            throw new IllegalStateException("retail bytes or INT3 padding changed at 0x005b6e00");
        }
        if (listing.getInstructionAt(entry) != null) {
            throw new IllegalStateException("0x005b6e00 is unexpectedly already disassembled");
        }

        int transaction = currentProgram.startTransaction("Define verified FUN_005b6e00");
        boolean commit = false;
        try {
            // Ghidra had classified each byte as DataDB. Clear only the six-byte
            // function; preserve the following INT3 alignment padding.
            clearListing(entry, toAddr(ENTRY + 5));
            if (!disassemble(entry)) {
                throw new IllegalStateException("Ghidra could not disassemble verified entry bytes");
            }

            requireInstruction(listing, ENTRY, "LEA", "8d4110", 3);
            requireInstruction(listing, ENTRY + 3, "RET", "c20800", 3);
            Function function = createFunction(entry, "FUN_005b6e00");
            if (function == null) {
                throw new IllegalStateException("Ghidra did not create FUN_005b6e00");
            }
            function.setCallingConvention("__thiscall");
            if (function.getBody().getNumAddresses() != 6 ||
                    !function.getBody().contains(toAddr(ENTRY + 5)) ||
                    function.getBody().contains(toAddr(ENTRY + 6)) ||
                    !"__thiscall".equals(function.getCallingConventionName())) {
                throw new IllegalStateException("new function body or calling convention is unexpected");
            }
            commit = true;
            println("Defined FUN_005b6e00 from verified LEA/RET bytes; body bytes=" +
                    function.getBody().getNumAddresses());
        }
        finally {
            currentProgram.endTransaction(transaction, commit);
        }
    }

    private void requireInstruction(Listing listing, long address, String mnemonic,
                                   String expectedBytes, int length) throws Exception {
        Instruction instruction = listing.getInstructionAt(toAddr(address));
        if (instruction == null || instruction.getLength() != length ||
                !mnemonic.equals(instruction.getMnemonicString()) ||
                !expectedBytes.equals(hex(instruction.getBytes()))) {
            throw new IllegalStateException("instruction mismatch at " + toAddr(address));
        }
    }

    private String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) value.append(String.format("%02x", item & 0xff));
        return value.toString();
    }
}
