// Define the retail indirect-call target at 0x00664e00 from its pinned bytes.
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

public class DefineShiftFunctionBody00664E00 extends GhidraScript {
    private static final String VERIFIED_00664E00 =
        "56ba02000000e865feffff8bf085f6741c8b068b50348bceffd285c0" +
        "8b068bce5e74058b5034ffe28b500cffe233c05ec3";
    private static final String VERIFIED_00664E40 =
        "56ba01000000e825feffff8bf085f6741c8b068b50348bceffd285c0" +
        "8b068bce5e74058b5034ffe28b500cffe233c05ec3";

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException(
                "Usage: DefineShiftFunctionBody00664E00.java <0x00664e00|0x00664e40>");
        }
        String token = args[0].toLowerCase();
        if (token.startsWith("0x")) token = token.substring(2);
        long entryOffset = Long.parseUnsignedLong(token, 16);
        String verifiedBytes;
        if (entryOffset == 0x00664e00L) verifiedBytes = VERIFIED_00664E00;
        else if (entryOffset == 0x00664e40L) verifiedBytes = VERIFIED_00664E40;
        else throw new IllegalArgumentException("unsupported verified entry " + args[0]);
        long endOffset = entryOffset + 0x30;
        Address entry = toAddr(entryOffset);
        Address end = toAddr(endOffset);
        FunctionManager functions = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();
        Memory memory = currentProgram.getMemory();
        Function existing = functions.getFunctionAt(entry);
        if (existing != null || functions.getFunctionContaining(entry) != null) {
            throw new IllegalStateException(entry + " already belongs to a function");
        }

        byte[] bytes = new byte[verifiedBytes.length() / 2];
        memory.getBytes(entry, bytes);
        if (!verifiedBytes.equals(hex(bytes))) {
            throw new IllegalStateException("retail bytes changed at " + entry);
        }

        int transaction = currentProgram.startTransaction(
            "Define verified " + entry);
        boolean commit = false;
        try {
            clearListing(entry, end);
            Address cursor = entry;
            int instructionCount = 0;
            Instruction last = null;
            while (cursor.compareTo(end) <= 0) {
                if (!disassemble(cursor)) {
                    throw new IllegalStateException("cannot disassemble " + cursor);
                }
                Instruction instruction = listing.getInstructionAt(cursor);
                if (instruction == null || instruction.getMaxAddress().compareTo(end) > 0) {
                    throw new IllegalStateException("instruction coverage gap at " + cursor);
                }
                last = instruction;
                instructionCount++;
                cursor = instruction.getMaxAddress().next();
            }
            if (last == null || !last.getMaxAddress().equals(end) ||
                    !"RET".equals(last.getMnemonicString()) || instructionCount != 22) {
                throw new IllegalStateException("function terminal or instruction count changed");
            }

            Function function = functions.createFunction(
                "FUN_" + String.format("%08x", entryOffset),
                entry, new AddressSet(entry, end),
                SourceType.USER_DEFINED);
            if (function == null) throw new IllegalStateException("function creation failed");
            function.setCallingConvention("__thiscall");
            if (function.getBody().getNumAddresses() != bytes.length ||
                    !end.equals(function.getBody().getMaxAddress()) ||
                    !"__thiscall".equals(function.getCallingConventionName())) {
                throw new IllegalStateException("created function body is not exact");
            }
            commit = true;
            println("Defined verified FUN_" + String.format("%08x", entryOffset) +
                    "; bytes=" + bytes.length +
                    " instructions=" + instructionCount);
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
